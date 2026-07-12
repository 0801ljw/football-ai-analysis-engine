from pathlib import Path
import threading
import time
import zipfile

import pytest

from app.run_manager import RunManager, classify_run_failure


def test_dry_run_create_writes_request_and_log_only(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    result = manager.create_run(["086", "087"], "世界杯数据推演", theme="dark", dry_run=True, timeout=12)

    run_dir = tmp_path / "runs" / result["run_id"]
    assert result["status"] == "dry_run"
    assert run_dir.exists()
    assert (run_dir / "request.json").exists()
    assert (run_dir / "log.json").exists()
    assert not (run_dir / "odds.json").exists()
    assert not (run_dir / "report.html").exists()

    detail = manager.get_run(result["run_id"])
    assert detail["request"]["nums"] == ["086", "087"]
    assert detail["request"]["dry_run"] is True
    assert detail["log"]["status"] == "dry_run"
    assert detail["log"]["artifacts"]["odds_path"] == str(run_dir / "odds.json")
    assert detail["log"]["artifacts"]["valid_odds_path"] == str(run_dir / "odds.valid.json")
    assert detail["log"]["artifacts"]["source_odds_path"] == str(run_dir / "odds.json")
    assert detail["log"]["artifacts"]["report_odds_path"] == str(run_dir / "odds.valid.json")
    assert detail["log"]["artifacts"]["report_path"] == str(run_dir / "report.html")
    assert detail["log"]["artifacts"]["report_url"] == "/runs/{}/report.html".format(result["run_id"])
    assert detail["log"]["safety"] == {"max_run_matches": 8, "timeout": 12, "dry_run": True}
    assert detail["paths"]["odds_path"] == str(run_dir / "odds.json")
    assert detail["paths"]["report_path"] == str(run_dir / "report.html")
    assert detail["paths"]["log_path"] == str(run_dir / "log.json")
    assert "fetch_odds" in detail["log"]["steps"]
    assert "generate_report" in detail["log"]["steps"]


def test_create_run_rejects_too_many_matches(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    with pytest.raises(ValueError, match="at most 8"):
        manager.create_run(["001", "002", "003", "004", "005", "006", "007", "008", "009"], "too many")


def test_create_run_rejects_invalid_theme(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    with pytest.raises(ValueError, match="theme"):
        manager.create_run(["086"], "bad theme", theme="light")


def test_list_runs_is_newest_first_and_includes_status(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    first = manager.create_run(["086"], "first", dry_run=True)
    second = manager.create_run(["087"], "second", dry_run=True)

    runs = manager.list_runs()

    assert [item["run_id"] for item in runs] == [second["run_id"], first["run_id"]]
    assert runs[0]["status"] == "dry_run"
    assert runs[0]["title"] == "second"


def test_get_run_rejects_path_traversal(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    for value in ["../secret", "nested/path", "%2e%2e", "bad id"]:
        with pytest.raises(ValueError):
            manager.get_run(value)


def test_create_run_executes_services_when_dry_run_false(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    def fake_fetch(self, nums, out=None, timeout=30):
        assert nums == ["086"]
        assert out is not None
        assert timeout == 19
        out.write_text('{"matches":{"086":{"主队":"巴西","客队":"德国","胜平负":{},"让球":{},"总进球":{},"比分波胆":{}}}}', encoding="utf-8")
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    def fake_report(self, odds_path, out_path, title, theme="dark", intel_path=None, timeout=30):
        assert odds_path.exists()
        assert title == "世界杯数据推演"
        assert theme == "blue"
        assert timeout == 19
        out_path.write_text("<html>report</html>", encoding="utf-8")
        return {"ok": True, "command": ["report"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)
    monkeypatch.setattr("app.run_manager.ReportService.generate_report_file", fake_report)

    result = manager.create_run(["086"], "世界杯数据推演", theme="blue", dry_run=False, timeout=19)

    run_dir = tmp_path / "runs" / result["run_id"]
    assert result["status"] == "succeeded"
    assert result["report_url"] == f"/runs/{result['run_id']}/report.html"
    assert (run_dir / "odds.json").exists()
    assert (run_dir / "odds.valid.json").exists()
    assert (run_dir / "report.html").exists()
    detail = manager.get_run(result["run_id"])
    assert detail["log"]["status"] == "succeeded"
    assert detail["log"]["started_at"]
    assert detail["log"]["finished_at"]
    assert detail["log"]["duration_seconds"] >= 0
    assert detail["log"]["steps"]["fetch_odds"]["ok"] is True
    assert detail["log"]["steps"]["generate_report"]["ok"] is True
    assert detail["log"]["odds_health"]["valid_count"] == 1
    assert detail["artifacts"]["report_url"] == f"/runs/{result['run_id']}/report.html"
    assert (run_dir / "prediction.json").exists()
    assert detail["artifacts"]["prediction_exists"] is True
    assert detail["data_quality"]["grade"] == "A"
    assert detail["data_quality"]["status"] == "publishable"
    assert detail["log"]["artifacts"]["prediction_path"] == str(run_dir / "prediction.json")


def test_create_run_marks_partial_when_fetch_ok_but_odds_missing(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    def fake_fetch(self, nums, out=None, timeout=30):
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)

    result = manager.create_run(["086"], "世界杯数据推演", dry_run=False)

    assert result["status"] == "partial"
    assert result["log"]["warning"]["code"] == "odds_missing"
    assert "generate_report" not in result["log"]["steps"]


def test_create_run_stops_when_fetch_ok_but_odds_has_no_valid_matches(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    def fake_fetch(self, nums, out=None, timeout=30):
        assert out is not None
        out.write_text('{"matches":{"086":{"error":"未在受注列表中找到该编号"}}}', encoding="utf-8")
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    def fail_report(*args, **kwargs):
        raise AssertionError("report generation should not be called")

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)
    monkeypatch.setattr("app.run_manager.ReportService.generate_report_file", fail_report)

    result = manager.create_run(["086"], "世界杯数据推演", dry_run=False)

    run_dir = tmp_path / "runs" / result["run_id"]
    assert result["status"] == "partial_no_valid_matches"
    assert result["log"]["warning"]["code"] == "no_valid_matches"
    assert result["log"]["odds_health"]["ok"] is False
    assert result["log"]["odds_health"]["invalid_count"] == 1
    assert not (run_dir / "odds.valid.json").exists()
    assert "generate_report" not in result["log"]["steps"]


def test_create_run_filters_invalid_matches_before_report(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    def fake_fetch(self, nums, out=None, timeout=30):
        assert out is not None
        out.write_text(
            '{"matches":{"086":{"error":"未在受注列表中找到该编号"},"091":{"主队":"阿根廷","客队":"法国"}}}',
            encoding="utf-8",
        )
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    def fake_report(self, odds_path, out_path, title, theme="dark", intel_path=None, timeout=30):
        assert odds_path.name == "odds.valid.json"
        payload = odds_path.read_text(encoding="utf-8")
        assert '"091"' in payload
        assert '"086"' not in payload
        out_path.write_text("<html>report</html>", encoding="utf-8")
        return {"ok": True, "command": ["report"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)
    monkeypatch.setattr("app.run_manager.ReportService.generate_report_file", fake_report)

    result = manager.create_run(["086", "091"], "世界杯数据推演", dry_run=False)

    run_dir = tmp_path / "runs" / result["run_id"]
    assert result["status"] == "succeeded"
    assert (run_dir / "odds.json").exists()
    assert (run_dir / "odds.valid.json").exists()
    assert result["log"]["warning"]["code"] == "some_invalid_matches"
    assert result["log"]["odds_health"]["valid_nums"] == ["091"]
    assert result["log"]["artifacts"]["source_odds_path"] == str(run_dir / "odds.json")
    assert result["log"]["artifacts"]["report_odds_path"] == str(run_dir / "odds.valid.json")


def test_background_create_returns_queued_and_updates_log(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")

    def fake_fetch(self, nums, out=None, timeout=30):
        assert out is not None
        out.write_text('{"matches":{"086":{"主队":"巴西","客队":"德国"}}}', encoding="utf-8")
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    def fake_report(self, odds_path, out_path, title, theme="dark", intel_path=None, timeout=30):
        out_path.write_text("<html>report</html>", encoding="utf-8")
        return {"ok": True, "command": ["report"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)
    monkeypatch.setattr("app.run_manager.ReportService.generate_report_file", fake_report)

    result = manager.create_run(["086"], "世界杯数据推演", dry_run=False, background=True)

    assert result["status"] == "queued"
    assert result["request"]["background"] is True
    assert result["log"]["status"] == "queued"

    deadline = time.time() + 3
    detail = manager.get_run(result["run_id"])
    while detail["status"] in {"queued", "running_fetch", "running_report"} and time.time() < deadline:
        time.sleep(0.02)
        detail = manager.get_run(result["run_id"])

    assert detail["status"] == "succeeded"
    assert detail["log"]["steps"]["fetch_odds"]["ok"] is True
    assert detail["log"]["steps"]["generate_report"]["ok"] is True


def test_retry_run_creates_new_background_run_from_failed_request(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr(manager, "_start_worker", lambda: None)
    failed = manager.create_run(["086", "091"], "世界杯数据推演", theme="blue", dry_run=True, timeout=17)
    failed_dir = tmp_path / "runs" / failed["run_id"]
    request = manager._read_json(failed_dir / "request.json")
    request["dry_run"] = False
    request["background"] = False
    manager._write_json(failed_dir / "request.json", request)
    log = manager._read_json(failed_dir / "log.json")
    log["status"] = "failed"
    manager._write_json(failed_dir / "log.json", log)

    retried = manager.retry_run(failed["run_id"])

    assert retried["run_id"] != failed["run_id"]
    assert retried["status"] == "queued"
    assert retried["request"]["nums"] == ["086", "091"]
    assert retried["request"]["title"] == "世界杯数据推演"
    assert retried["request"]["theme"] == "blue"
    assert retried["request"]["dry_run"] is False
    assert retried["request"]["background"] is True
    assert retried["request"]["timeout"] == 17
    assert retried["request"]["retry_of"] == failed["run_id"]
    assert retried["log"]["retry_of"] == failed["run_id"]
    assert manager.get_run(failed["run_id"])["status"] == "failed"


@pytest.mark.parametrize("status", ["failed", "partial", "partial_no_valid_matches", "cancelled"])
def test_retry_run_allows_terminal_non_success_statuses(status: str, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    original = manager.create_run(["086"], "世界杯数据推演", dry_run=True)
    run_dir = tmp_path / "runs" / original["run_id"]
    log = manager._read_json(run_dir / "log.json")
    log["status"] = status
    manager._write_json(run_dir / "log.json", log)

    retried = manager.retry_run(original["run_id"])

    assert retried["run_id"] != original["run_id"]
    assert retried["request"]["retry_of"] == original["run_id"]


@pytest.mark.parametrize("status", ["succeeded", "dry_run", "queued", "running_fetch", "running_report"])
def test_retry_run_rejects_success_dry_run_and_active_statuses(status: str, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    original = manager.create_run(["086"], "世界杯数据推演", dry_run=True)
    run_dir = tmp_path / "runs" / original["run_id"]
    log = manager._read_json(run_dir / "log.json")
    log["status"] = status
    manager._write_json(run_dir / "log.json", log)

    with pytest.raises(ValueError, match="cannot retry"):
        manager.retry_run(original["run_id"])


def test_cancel_run_marks_queued_run_cancelled(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    queued = manager.create_run(["086"], "世界杯数据推演", dry_run=True)
    run_dir = tmp_path / "runs" / queued["run_id"]
    log = manager._read_json(run_dir / "log.json")
    log["status"] = "queued"
    manager._write_json(run_dir / "log.json", log)

    cancelled = manager.cancel_run(queued["run_id"], reason="user_requested")

    assert cancelled["status"] == "cancelled"
    assert cancelled["log"]["cancelled_at"]
    assert cancelled["log"]["cancellation"]["reason"] == "user_requested"


def test_cancel_run_marks_running_run_cancel_requested(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    running = manager.create_run(["086"], "世界杯数据推演", dry_run=True)
    run_dir = tmp_path / "runs" / running["run_id"]
    log = manager._read_json(run_dir / "log.json")
    log["status"] = "running_fetch"
    manager._write_json(run_dir / "log.json", log)

    detail = manager.cancel_run(running["run_id"], reason="user_requested")

    assert detail["status"] == "running_fetch"
    assert detail["log"]["cancel_requested"] is True
    assert detail["log"]["cancel_requested_at"]
    assert detail["log"]["cancellation"]["reason"] == "user_requested"
    assert "warning" in detail


def test_recover_pending_runs_requeues_queued_and_marks_stale_running(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr(manager, "_start_workers", lambda: None)
    queued = manager.create_run(["086"], "queued", dry_run=True)
    running = manager.create_run(["087"], "running", dry_run=True)
    terminal = manager.create_run(["088"], "terminal", dry_run=True)

    for run_id, status in [
        (queued["run_id"], "queued"),
        (running["run_id"], "running_fetch"),
        (terminal["run_id"], "succeeded"),
    ]:
        run_dir = tmp_path / "runs" / run_id
        log = manager._read_json(run_dir / "log.json")
        log["status"] = status
        manager._write_json(run_dir / "log.json", log)

    result = manager.recover_pending_runs()
    second = manager.recover_pending_runs()

    assert result["recovered_count"] == 1
    assert result["marked_failed_count"] == 1
    assert result["recovered_run_ids"] == [queued["run_id"]]
    assert result["marked_failed_run_ids"] == [running["run_id"]]
    assert manager.get_run(queued["run_id"])["status"] == "queued"
    running_detail = manager.get_run(running["run_id"])
    assert running_detail["status"] == "failed"
    assert running_detail["log"]["error"]["code"] == "interrupted"
    assert "process stopped before completion" in running_detail["log"]["error"]["message"]
    assert manager.get_run(terminal["run_id"])["status"] == "succeeded"
    assert second["recovered_count"] == 0
    assert second["marked_failed_count"] == 0


def test_queue_stats_and_concurrency_limit_run_background_jobs_sequentially(monkeypatch, tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs", max_concurrent_runs=1)
    release_fetch = threading.Event()
    fetch_order = []
    report_order = []

    def fake_fetch(self, nums, out=None, timeout=30):
        fetch_order.append(nums[0])
        assert out is not None
        release_fetch.wait(2)
        out.write_text(f'{{"matches":{{"{nums[0]}":{{"主队":"巴西","客队":"德国"}}}}}}', encoding="utf-8")
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    def fake_report(self, odds_path, out_path, title, theme="dark", intel_path=None, timeout=30):
        report_order.append(title)
        out_path.write_text("<html>report</html>", encoding="utf-8")
        return {"ok": True, "command": ["report"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)
    monkeypatch.setattr("app.run_manager.ReportService.generate_report_file", fake_report)

    first = manager.create_run(["086"], "first", dry_run=False, background=True)
    second = manager.create_run(["087"], "second", dry_run=False, background=True)

    deadline = time.time() + 2
    stats = manager.queue_stats()
    while stats["active_count"] != 1 and time.time() < deadline:
        time.sleep(0.02)
        stats = manager.queue_stats()

    assert stats["max_concurrent_runs"] == 1
    assert stats["active_run_ids"] == [first["run_id"]]
    assert stats["queued_run_ids"] == [second["run_id"]]
    assert manager.get_run(second["run_id"])["status"] == "queued"

    release_fetch.set()
    deadline = time.time() + 3
    while manager.get_run(second["run_id"])["status"] != "succeeded" and time.time() < deadline:
        time.sleep(0.02)

    assert manager.get_run(first["run_id"])["status"] == "succeeded"
    assert manager.get_run(second["run_id"])["status"] == "succeeded"
    assert fetch_order == ["086", "087"]
    assert report_order == ["first", "second"]


def test_failure_classifier_and_failure_dashboard(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    failed = manager.create_run(["086"], "fetch failed", dry_run=True)
    partial = manager.create_run(["087"], "missing odds", dry_run=True)
    cancelled = manager.create_run(["088"], "cancelled", dry_run=True)

    updates = [
        (failed["run_id"], {"status": "failed", "steps": {"fetch_odds": {"ok": False, "error": {"code": "script_unavailable", "message": "missing"}}}}),
        (partial["run_id"], {"status": "partial", "warning": {"code": "odds_missing", "message": "missing odds"}}),
        (cancelled["run_id"], {"status": "cancelled", "cancellation": {"reason": "user_requested"}}),
    ]
    for run_id, patch in updates:
        run_dir = tmp_path / "runs" / run_id
        log = manager._read_json(run_dir / "log.json")
        log.update(patch)
        manager._write_json(run_dir / "log.json", log)

    assert classify_run_failure({"status": "partial_no_valid_matches", "warning": {"code": "no_valid_matches"}}) == "no_valid_matches"

    failures = manager.failure_dashboard()

    assert failures["counts"] == {"cancelled": 1, "odds_missing": 1, "script_unavailable": 1}
    assert [item["category"] for item in failures["recent"]] == ["cancelled", "odds_missing", "script_unavailable"]
    assert failures["recent"][0]["title"] == "cancelled"
    assert failures["recent"][1]["summary"] == "missing odds"


def test_export_zip_contains_available_run_artifacts(tmp_path: Path):
    manager = RunManager(root=tmp_path / "runs")
    run = manager.create_run(["086"], "世界杯数据推演", dry_run=True)
    run_dir = tmp_path / "runs" / run["run_id"]
    (run_dir / "odds.json").write_text('{"matches":{}}', encoding="utf-8")
    (run_dir / "prediction.json").write_text('{"schema_version":"1.0","data_quality":{"grade":"B","status":"publishable"}}', encoding="utf-8")

    zip_bytes = manager.export_zip(run["run_id"])
    zip_path = tmp_path / "export.zip"
    zip_path.write_bytes(zip_bytes)

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        manifest = archive.read("manifest.json").decode("utf-8")

    assert {"manifest.json", "request.json", "log.json", "odds.json", "prediction.json"}.issubset(names)
    assert "report.html" not in names
    assert run["run_id"] in manifest
    assert "prediction.json" in manifest
