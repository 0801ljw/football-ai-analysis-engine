from __future__ import annotations

import json
import queue
import re
import threading
import uuid
import zipfile
from io import BytesIO
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.odds_health import filter_valid_odds_payload, inspect_odds_payload, load_odds_file
from app.prediction import build_prediction
from app.run_index import RunIndex
from app.report_service import ReportService
from app.report_service import ALLOWED_THEMES
from app.skill_bridge import SkillBridge
from app.sporttery_service import SportteryService


RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
RETRYABLE_STATUSES = {"failed", "partial", "partial_no_valid_matches", "cancelled"}
NON_RETRYABLE_STATUSES = {"succeeded", "dry_run", "queued", "running_fetch", "running_report"}
TERMINAL_STATUSES = {"succeeded", "dry_run", "failed", "partial", "partial_no_valid_matches", "cancelled"}
ACTIVE_STATUSES = {"running_fetch", "running_report"}
FAILURE_DASHBOARD_STATUSES = {"failed", "partial", "partial_no_valid_matches", "cancelled"}
EXPORT_ARTIFACTS = ("request.json", "log.json", "odds.json", "odds.valid.json", "report.html", "prediction.json")


def classify_run_failure(log: dict) -> str:
    status = str(log.get("status") or "unknown")
    if status == "cancelled":
        return "cancelled"

    candidates: list[dict] = []
    for key in ("error", "warning"):
        value = log.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    steps = log.get("steps")
    if isinstance(steps, dict):
        for step in ("fetch_odds", "generate_report"):
            value = steps.get(step)
            if not isinstance(value, dict):
                continue
            if isinstance(value.get("error"), dict):
                candidates.append(value["error"])
            candidates.append(value)

    for item in candidates:
        code = str(item.get("code") or "")
        if code in {
            "script_unavailable",
            "fetch_failed",
            "odds_missing",
            "no_valid_matches",
            "report_missing",
            "cancelled",
            "interrupted",
        }:
            return code
        message = str(item.get("message") or item.get("stderr") or item.get("stdout") or "").lower()
        if "fetch" in message and "fail" in message:
            return "fetch_failed"
        if "odds" in message and "missing" in message:
            return "odds_missing"
        if "report" in message and "missing" in message:
            return "report_missing"

    if status == "partial_no_valid_matches":
        return "no_valid_matches"
    if status == "failed":
        return "fetch_failed" if "fetch_odds" in str(log.get("steps", {})) else "unknown"
    return "unknown"


def summarize_run_failure(log: dict) -> str:
    for key in ("error", "warning"):
        value = log.get(key)
        if isinstance(value, dict) and value.get("message"):
            return str(value["message"])
    steps = log.get("steps")
    if isinstance(steps, dict):
        for step in ("fetch_odds", "generate_report"):
            value = steps.get(step)
            if not isinstance(value, dict):
                continue
            error = value.get("error")
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"])
            if value.get("stderr"):
                return str(value["stderr"]).strip()
    return ""


class RunManager:
    def __init__(
        self,
        root: Path | None = None,
        sporttery_service: SportteryService | None = None,
        report_service: ReportService | None = None,
        max_concurrent_runs: int | None = None,
        auto_recover: bool = False,
    ):
        settings = get_settings()
        bridge = SkillBridge(settings.skill_path)
        self.root = root or settings.runs_path
        self.max_run_matches = settings.max_run_matches
        self.max_concurrent_runs = max(1, int(max_concurrent_runs or settings.max_concurrent_runs))
        self.default_command_timeout = settings.default_command_timeout
        self.index = RunIndex(settings.db_path)
        self.sporttery_service = sporttery_service or SportteryService(bridge)
        self.report_service = report_service or ReportService(bridge)
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker_started = 0
        self._worker_lock = threading.Lock()
        self._queued_run_ids: set[str] = set()
        self._queued_lock = threading.Lock()
        if auto_recover:
            self.recover_pending_runs()

    def create_run(
        self,
        nums: list[str],
        title: str,
        theme: str = "dark",
        dry_run: bool = True,
        background: bool = False,
        timeout: int | None = None,
        retry_of: str | None = None,
        owner_user_id: str = "",
        owner_username: str = "",
    ) -> dict:
        self._validate_run_input(nums, theme)
        command_timeout = timeout if timeout is not None else self.default_command_timeout
        run_id = self._initialize_run(
            nums,
            title,
            theme,
            dry_run,
            background,
            timeout,
            command_timeout,
            retry_of,
            owner_user_id,
            owner_username,
        )
        if background and not dry_run:
            queued_detail = self.get_run(run_id)
            self._enqueue_run(run_id)
            return queued_detail
        self._execute_run(run_id)
        return self.get_run(run_id)

    def retry_run(self, run_id: str) -> dict:
        detail = self.get_run(run_id)
        status = detail.get("status")
        if status not in RETRYABLE_STATUSES:
            if status in NON_RETRYABLE_STATUSES:
                raise ValueError(f"cannot retry run with status {status}")
            raise ValueError(f"cannot retry run with non-terminal status {status}")
        request = detail["request"]
        dry_run = bool(request.get("dry_run", True))
        background = bool(request.get("background", False))
        if not dry_run:
            background = True
        return self.create_run(
            nums=list(request.get("nums", [])),
            title=request.get("title", ""),
            theme=request.get("theme", "dark"),
            dry_run=dry_run,
            background=background,
            timeout=request.get("timeout"),
            retry_of=run_id,
            owner_user_id=request.get("owner_user_id", ""),
            owner_username=request.get("owner_username", ""),
        )

    def cancel_run(self, run_id: str, reason: str = "user_requested") -> dict:
        run_dir = self._run_dir(run_id)
        log_path = run_dir / "log.json"
        if not log_path.exists():
            raise FileNotFoundError(run_id)
        log = self._read_json(log_path)
        status = log.get("status", "unknown")
        now = self._now_iso()
        if status == "queued":
            log["status"] = "cancelled"
            log["cancelled_at"] = now
            log["cancellation"] = {"reason": reason}
            self._write_json(log_path, log)
            with self._queued_lock:
                self._queued_run_ids.discard(run_id)
            return self.get_run(run_id)
        if status in {"running_fetch", "running_report"}:
            log["cancel_requested"] = True
            log["cancel_requested_at"] = now
            log["cancellation"] = {"reason": reason}
            self._write_json(log_path, log)
            detail = self.get_run(run_id)
            detail["warning"] = "cancel requested; worker will stop before the next stage if possible"
            return detail
        detail = self.get_run(run_id)
        if status in TERMINAL_STATUSES:
            detail["warning"] = f"run already terminal with status {status}; cancellation unchanged"
            return detail
        raise ValueError(f"cannot cancel run with status {status}")

    def recover_pending_runs(self) -> dict:
        recovered_run_ids = []
        marked_failed_run_ids = []
        now = self._now_iso()
        if not self.root.exists():
            return {
                "recovered_count": 0,
                "marked_failed_count": 0,
                "recovered_run_ids": [],
                "marked_failed_run_ids": [],
            }

        for log_path in sorted(self.root.glob("*/log.json")):
            run_id = log_path.parent.name
            if not (log_path.parent / "request.json").exists():
                continue
            try:
                log = self._read_json(log_path)
            except (json.JSONDecodeError, OSError):
                continue
            status = log.get("status")
            if status == "queued":
                if self._enqueue_run(run_id):
                    recovered_run_ids.append(run_id)
                continue
            if status in ACTIVE_STATUSES:
                log["status"] = "failed"
                log["finished_at"] = now
                log["error"] = {
                    "code": "interrupted",
                    "message": "Previous process stopped before completion; retry this run to start a fresh execution.",
                }
                self._write_json(log_path, log)
                marked_failed_run_ids.append(run_id)

        return {
            "recovered_count": len(recovered_run_ids),
            "marked_failed_count": len(marked_failed_run_ids),
            "recovered_run_ids": recovered_run_ids,
            "marked_failed_run_ids": marked_failed_run_ids,
        }

    def queue_stats(self) -> dict:
        queued_run_ids = []
        active_run_ids = []
        if self.root.exists():
            for log_path in sorted(self.root.glob("*/log.json")):
                run_id = log_path.parent.name
                try:
                    log = self._read_json(log_path)
                except (json.JSONDecodeError, OSError):
                    continue
                status = log.get("status")
                if status == "queued":
                    queued_run_ids.append(run_id)
                elif status in ACTIVE_STATUSES:
                    active_run_ids.append(run_id)
        return {
            "queued_count": len(queued_run_ids),
            "active_count": len(active_run_ids),
            "max_concurrent_runs": self.max_concurrent_runs,
            "queued_run_ids": queued_run_ids,
            "active_run_ids": active_run_ids,
        }

    def failure_dashboard(self, limit: int = 20) -> dict:
        recent = []
        counts: dict[str, int] = {}
        for detail in self._iter_run_details():
            status = detail.get("status")
            log = detail.get("log", {})
            if status not in FAILURE_DASHBOARD_STATUSES:
                continue
            category = classify_run_failure(log)
            counts[category] = counts.get(category, 0) + 1
            request = detail.get("request", {})
            recent.append(
                {
                    "run_id": detail["run_id"],
                    "category": category,
                    "status": status,
                    "title": request.get("title"),
                    "nums": request.get("nums", []),
                    "created_at": detail.get("created_at"),
                    "summary": summarize_run_failure(log),
                }
            )
        recent = sorted(recent, key=lambda item: (item.get("created_at") or "", item["run_id"]), reverse=True)
        return {"counts": dict(sorted(counts.items())), "recent": recent[:limit]}

    def export_zip(self, run_id: str) -> bytes:
        run_dir = self._run_dir(run_id)
        if not (run_dir / "request.json").exists():
            raise FileNotFoundError(run_id)
        detail = self.get_run(run_id)
        files = [name for name in EXPORT_ARTIFACTS if (run_dir / name).exists()]
        manifest = {
            "run_id": run_id,
            "status": detail.get("status"),
            "files": files,
            "generated_at": self._now_iso(),
        }
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for name in files:
                archive.write(run_dir / name, arcname=name)
        return buffer.getvalue()

    def rebuild_index(self) -> dict:
        count = 0
        for detail in self._iter_run_details():
            self._index_detail(detail)
            count += 1
        return {"indexed": count, "index": self.index.stats()}

    def search_runs(
        self,
        status: str = "",
        num: str = "",
        quality: str = "",
        q: str = "",
        owner_user_id: str = "",
    ) -> list[dict]:
        rows = self.index.query(status=status, num=num, quality=quality, q=q, owner_user_id=owner_user_id)
        results = []
        for row in rows:
            try:
                results.append(self._summary(self.get_run(row["run_id"])))
            except Exception:
                results.append(row)
        return results

    def _index_detail(self, detail: dict) -> None:
        failure = classify_run_failure(detail.get("log", {})) if detail.get("status") in FAILURE_DASHBOARD_STATUSES else ""
        self.index.upsert(detail, failure)

    def _execute_run(self, run_id: str) -> None:
        run_dir = self._run_dir(run_id)
        request_path = run_dir / "request.json"
        log_path = run_dir / "log.json"
        request = self._read_json(request_path)
        log = self._read_json(log_path)
        nums = request["nums"]
        title = request["title"]
        theme = request["theme"]
        dry_run = bool(request.get("dry_run", True))
        command_timeout = log.get("safety", {}).get("timeout", self.default_command_timeout)
        odds_path = run_dir / "odds.json"
        valid_odds_path = run_dir / "odds.valid.json"
        report_path = run_dir / "report.html"
        prediction_path = run_dir / "prediction.json"
        try:
            fetch_command = self.sporttery_service.build_fetch_odds_command(nums, odds_path)
            report_command = self.report_service.build_report_command(valid_odds_path, report_path, title, theme)
            if dry_run:
                log["status"] = "dry_run"
                log["steps"] = {
                    "fetch_odds": {"dry_run": True, "command": fetch_command},
                    "generate_report": {"dry_run": True, "command": report_command},
                }
            else:
                started_at = datetime.now(UTC)
                log["started_at"] = started_at.isoformat().replace("+00:00", "Z")
                if self._cancel_requested(log_path):
                    log = self._mark_cancelled_before_stage(log_path, "fetch_odds", started_at)
                    return
                log["status"] = "running_fetch"
                self._write_json(log_path, log)
                fetch_result = self.sporttery_service.fetch_odds(nums, out=odds_path, timeout=command_timeout)
                log = self._merge_cancel_fields(log, self._read_json(log_path))
                log["steps"]["fetch_odds"] = fetch_result
                if self._cancel_requested(log_path, log):
                    log = self._mark_cancelled_before_stage(log_path, "generate_report", started_at, log)
                    return
                if fetch_result.get("ok") is True and odds_path.exists():
                    odds_payload = load_odds_file(odds_path)
                    health = inspect_odds_payload(odds_payload)
                    log["odds_health"] = health
                    if not health["ok"]:
                        log["status"] = "partial_no_valid_matches"
                        log["warning"] = {
                            "code": "no_valid_matches",
                            "message": health["summary"],
                            "health": health,
                        }
                    else:
                        self._write_json(valid_odds_path, filter_valid_odds_payload(odds_payload, health["valid_nums"]))
                        if health["invalid_count"] > 0:
                            log["warning"] = {
                                "code": "some_invalid_matches",
                                "message": health["summary"],
                                "health": health,
                            }
                        log["artifacts"]["source_odds_path"] = str(odds_path)
                        log["artifacts"]["report_odds_path"] = str(valid_odds_path)
                        log["status"] = "running_report"
                        self._write_json(log_path, log)
                        report_result = self.report_service.generate_report_file(
                            odds_path=valid_odds_path,
                            out_path=report_path,
                            title=title,
                            theme=theme,
                            timeout=command_timeout,
                        )
                        log = self._merge_cancel_fields(log, self._read_json(log_path))
                        log["steps"]["generate_report"] = report_result
                        if report_result.get("ok") is True and report_path.exists():
                            log["status"] = "succeeded"
                        else:
                            log["status"] = "partial"
                            if report_result.get("ok") is True:
                                log["warning"] = {
                                    "code": "report_missing",
                                    "message": "generate_report returned ok=true but report.html was not created",
                                }
                        if log["status"] in {"succeeded", "partial"}:
                            valid_odds_payload = load_odds_file(valid_odds_path) if valid_odds_path.exists() else {"matches": {}}
                            prediction = build_prediction(
                                run_id=run_id,
                                valid_odds_payload=valid_odds_payload,
                                odds_health=health,
                                odds_path=str(odds_path),
                                valid_odds_path=str(valid_odds_path),
                                report_path=str(report_path),
                            )
                            self._write_json(prediction_path, prediction)
                            log["artifacts"]["prediction_path"] = str(prediction_path)
                elif fetch_result.get("ok") is True:
                    log["status"] = "partial"
                    log["warning"] = {
                        "code": "odds_missing",
                        "message": "fetch_odds returned ok=true but odds.json was not created",
                    }
                else:
                    log["status"] = "failed"
                finished_at = datetime.now(UTC)
                log["finished_at"] = finished_at.isoformat().replace("+00:00", "Z")
                log["duration_seconds"] = round((finished_at - started_at).total_seconds(), 3)
        except Exception as exc:
            log["status"] = "failed"
            log["error"] = {"type": exc.__class__.__name__, "message": str(exc)}
            if not dry_run and "started_at" in log and "finished_at" not in log:
                finished_at = datetime.now(UTC)
                started_at = datetime.fromisoformat(log["started_at"].replace("Z", "+00:00"))
                log["finished_at"] = finished_at.isoformat().replace("+00:00", "Z")
                log["duration_seconds"] = round((finished_at - started_at).total_seconds(), 3)
        finally:
            self._write_json(log_path, log)
            try:
                self._index_detail(self.get_run(run_id))
            except Exception:
                pass

    def list_runs(self, owner_user_id: str = "") -> list[dict]:
        runs = [
            self._summary(detail)
            for detail in self._iter_run_details()
            if self._can_access_detail(detail, owner_user_id)
        ]
        return sorted(runs, key=lambda item: (item.get("created_at") or "", item["run_id"]), reverse=True)

    def get_run(self, run_id: str) -> dict:
        run_dir = self._run_dir(run_id)
        request_path = run_dir / "request.json"
        log_path = run_dir / "log.json"
        if not request_path.exists():
            raise FileNotFoundError(run_id)

        request = self._read_json(request_path)
        log = self._read_json(log_path) if log_path.exists() else {}
        odds_path = run_dir / "odds.json"
        valid_odds_path = run_dir / "odds.valid.json"
        report_path = run_dir / "report.html"
        prediction_path = run_dir / "prediction.json"
        artifacts = {
            "odds_exists": odds_path.exists(),
            "valid_odds_exists": valid_odds_path.exists(),
            "report_exists": report_path.exists(),
            "log_exists": log_path.exists(),
            "prediction_exists": prediction_path.exists(),
        }
        if report_path.exists():
            artifacts["report_url"] = self._report_url(run_id)
        prediction_summary = None
        data_trust = None
        source = None
        if prediction_path.exists():
            try:
                prediction_payload = self._read_json(prediction_path)
                prediction_summary = prediction_payload.get("data_quality")
                data_trust = prediction_payload.get("data_trust")
                source = prediction_payload.get("source")
            except (json.JSONDecodeError, OSError):
                prediction_summary = None
        return {
            "run_id": run_id,
            "created_at": request.get("created_at"),
            "status": log.get("status", "unknown"),
            "request": request,
            "owner": {
                "user_id": request.get("owner_user_id", ""),
                "username": request.get("owner_username", ""),
            },
            "log": log,
            "odds_health": self.odds_health(run_id, log),
            "report_url": self._report_url(run_id) if report_path.exists() else None,
            "data_quality": prediction_summary,
            "data_trust": data_trust,
            "source": source,
            "paths": {
                "odds_path": str(odds_path),
                "valid_odds_path": str(valid_odds_path),
                "report_path": str(report_path),
                "log_path": str(log_path),
                "prediction_path": str(prediction_path),
            },
            "artifacts": artifacts,
        }

    def report_file(self, run_id: str) -> Path | None:
        run_dir = self._run_dir(run_id)
        report_path = run_dir / "report.html"
        return report_path if report_path.exists() else None

    def odds_health(self, run_id: str, log: dict | None = None) -> dict | None:
        run_dir = self._run_dir(run_id)
        if log is None:
            log_path = run_dir / "log.json"
            log = self._read_json(log_path) if log_path.exists() else {}
        health = log.get("odds_health")
        if isinstance(health, dict):
            return health
        odds_path = run_dir / "odds.json"
        if odds_path.exists():
            return inspect_odds_payload(load_odds_file(odds_path))
        return None

    def prediction(self, run_id: str) -> dict | None:
        run_dir = self._run_dir(run_id)
        if not (run_dir / "request.json").exists():
            raise FileNotFoundError(run_id)
        prediction_path = run_dir / "prediction.json"
        if not prediction_path.exists():
            return None
        return self._read_json(prediction_path)

    def _iter_run_details(self) -> list[dict]:
        if not self.root.exists():
            return []
        details = []
        for request_path in self.root.glob("*/request.json"):
            run_id = request_path.parent.name
            try:
                details.append(self.get_run(run_id))
            except (FileNotFoundError, ValueError, json.JSONDecodeError):
                continue
        return details

    def _new_run_id(self) -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"{stamp}-{uuid.uuid4().hex[:6]}"

    def _run_dir(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("invalid run_id")
        root = self.root.resolve()
        run_dir = (self.root / run_id).resolve()
        if run_dir != root and root not in run_dir.parents:
            raise ValueError("invalid run_id")
        return run_dir

    def _summary(self, detail: dict) -> dict:
        request = detail.get("request", {})
        artifacts = detail.get("artifacts", {})
        return {
            "run_id": detail["run_id"],
            "created_at": detail.get("created_at"),
            "status": detail.get("status"),
            "title": request.get("title"),
            "theme": request.get("theme"),
            "dry_run": request.get("dry_run"),
            "nums": request.get("nums", []),
            "owner": {
                "user_id": request.get("owner_user_id", ""),
                "username": request.get("owner_username", ""),
            },
            "report_exists": artifacts.get("report_exists", False),
            "report_url": artifacts.get("report_url"),
            "odds_health": self._health_summary(detail.get("odds_health")),
            "prediction_exists": artifacts.get("prediction_exists", False),
            "data_quality": detail.get("data_quality"),
            "data_trust": detail.get("data_trust"),
        }

    @staticmethod
    def _health_summary(health: dict | None) -> dict | None:
        if not isinstance(health, dict):
            return None
        return {
            "ok": health.get("ok", False),
            "valid_count": health.get("valid_count", 0),
            "invalid_count": health.get("invalid_count", 0),
            "summary": health.get("summary", ""),
        }

    def _validate_run_input(self, nums: list[str], theme: str) -> None:
        self.sporttery_service.build_fetch_odds_command(nums, None)
        if len(nums) > self.max_run_matches:
            raise ValueError(f"nums may include at most {self.max_run_matches} match numbers")
        if theme not in ALLOWED_THEMES:
            raise ValueError("theme must be one of: blue, dark, purple")

    def _initialize_run(
        self,
        nums: list[str],
        title: str,
        theme: str,
        dry_run: bool,
        background: bool,
        timeout: int | None,
        command_timeout: int,
        retry_of: str | None = None,
        owner_user_id: str = "",
        owner_username: str = "",
    ) -> str:
        created_at = self._now_iso()
        run_id = self._new_run_id()
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=False)

        odds_path = run_dir / "odds.json"
        valid_odds_path = run_dir / "odds.valid.json"
        report_path = run_dir / "report.html"
        prediction_path = run_dir / "prediction.json"
        request_path = run_dir / "request.json"
        request = {
            "nums": nums,
            "title": title,
            "theme": theme,
            "dry_run": dry_run,
            "background": background,
            "timeout": timeout,
            "created_at": created_at,
            "owner_user_id": owner_user_id,
            "owner_username": owner_username,
        }
        if retry_of:
            request["retry_of"] = retry_of
        self._write_json(request_path, request)
        status = "queued" if background and not dry_run else "running"
        log: dict[str, Any] = {
            "run_id": run_id,
            "created_at": created_at,
            "status": status,
            "artifacts": {
                "odds_path": str(odds_path),
                "valid_odds_path": str(valid_odds_path),
                "source_odds_path": str(odds_path),
                "report_odds_path": str(valid_odds_path),
                "report_path": str(report_path),
                "prediction_path": str(prediction_path),
                "report_url": self._report_url(run_id),
            },
            "safety": {
                "max_run_matches": self.max_run_matches,
                "timeout": command_timeout,
                "dry_run": dry_run,
            },
            "steps": {},
        }
        if retry_of:
            log["retry_of"] = retry_of
        self._write_json(run_dir / "log.json", log)
        try:
            self._index_detail(self.get_run(run_id))
        except Exception:
            pass
        return run_id

    @staticmethod
    def _can_access_detail(detail: dict, owner_user_id: str = "") -> bool:
        if not owner_user_id:
            return True
        request = detail.get("request", {})
        return request.get("owner_user_id") == owner_user_id

    def _start_worker(self) -> None:
        self._start_workers()

    def _start_workers(self) -> None:
        with self._worker_lock:
            while self._worker_started < self.max_concurrent_runs:
                index = self._worker_started + 1
                thread = threading.Thread(target=self._worker_loop, name=f"run-manager-worker-{index}", daemon=True)
                thread.start()
                self._worker_started += 1

    def _enqueue_run(self, run_id: str) -> bool:
        self._start_worker()
        with self._queued_lock:
            if run_id in self._queued_run_ids:
                return False
            self._queued_run_ids.add(run_id)
        self._queue.put(run_id)
        return True

    def _worker_loop(self) -> None:
        while True:
            run_id = self._queue.get()
            try:
                detail = self.get_run(run_id)
                if detail["status"] == "cancelled":
                    continue
                self._execute_run(run_id)
            finally:
                with self._queued_lock:
                    self._queued_run_ids.discard(run_id)
                self._queue.task_done()

    def _cancel_requested(self, log_path: Path, log: dict | None = None) -> bool:
        current = log if log is not None else self._read_json(log_path)
        return current.get("status") == "cancelled" or current.get("cancel_requested") is True

    def _mark_cancelled_before_stage(
        self,
        log_path: Path,
        stage: str,
        started_at: datetime,
        log: dict | None = None,
    ) -> dict:
        current = log if log is not None else self._read_json(log_path)
        current["status"] = "cancelled"
        current["cancelled_at"] = self._now_iso()
        current["cancelled_before"] = stage
        current.setdefault("cancellation", {"reason": "user_requested"})
        finished_at = datetime.now(UTC)
        current["finished_at"] = finished_at.isoformat().replace("+00:00", "Z")
        current["duration_seconds"] = round((finished_at - started_at).total_seconds(), 3)
        self._write_json(log_path, current)
        return current

    @staticmethod
    def _merge_cancel_fields(log: dict, current: dict) -> dict:
        for key in ("cancel_requested", "cancel_requested_at", "cancelled_at", "cancelled_before", "cancellation"):
            if key in current:
                log[key] = current[key]
        if current.get("status") == "cancelled":
            log["status"] = "cancelled"
        return log

    @staticmethod
    def _report_url(run_id: str) -> str:
        return f"/runs/{run_id}/report.html"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)
