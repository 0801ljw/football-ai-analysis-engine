from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import tempfile

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import AuthManager
from app.config import ROOT_DIR, get_settings
from app.resources import resource_path
from app.commercial import UsageTracker
from app.data_source_status import PublicProbeTracker, build_desktop_data_status
from app.desktop_settings import ApiKeyStore, ApiKeyStoreUnavailable, build_api_key_store, validate_provider
from app.engine_adapter import WorldCupEngineAdapter
from app.odds_health import inspect_odds_payload, load_odds_file
from app.report_service import ReportService
from app.run_index import RunIndex
from app.run_manager import RunManager
from app.runtime_doctor import assert_safe_external_binding, build_runtime_report
from app.schemas import (
    DesktopApiKeyUpdateRequest,
    GenerateRequest,
    OddsDiscoverRequest,
    OddsFetchRequest,
    OddsInspectRequest,
    ReportBuildRequest,
    RunCreateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.setup_guide import build_setup_guide
from app.skill_bridge import SkillBridge
from app.sporttery_service import SportteryService


settings = get_settings()
_run_manager: RunManager | None = None
_run_index: RunIndex | None = None
_usage_tracker: UsageTracker | None = None
_auth_manager: AuthManager | None = None
_desktop_api_key_store: ApiKeyStore | None = None
_public_probe_tracker = PublicProbeTracker()




def get_auth_manager() -> AuthManager:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(settings.db_path)
    return _auth_manager


def get_desktop_api_key_store() -> ApiKeyStore:
    global _desktop_api_key_store
    if _desktop_api_key_store is None:
        _desktop_api_key_store = build_api_key_store(settings)
    return _desktop_api_key_store


def require_desktop_mode() -> None:
    if not settings.desktop_mode:
        raise HTTPException(status_code=404, detail="not found")


def _valid_desktop_provider(provider: str) -> str:
    try:
        return validate_provider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="unsupported api key provider") from exc


def current_user(x_api_token: str | None = Header(default=None)) -> dict:
    auth = get_auth_manager()
    if auth.has_users():
        user = auth.authenticate(x_api_token)
        if not user:
            raise HTTPException(status_code=401, detail="valid user X-API-Token required")
        return user
    if settings.api_token:
        if x_api_token != settings.api_token:
            raise HTTPException(status_code=401, detail="valid X-API-Token required")
        return {"user_id": "system", "username": "system", "role": "admin", "plan": settings.plan, "run_quota": settings.run_quota}
    return {"user_id": "anonymous", "username": "anonymous", "role": "admin", "plan": settings.plan, "run_quota": settings.run_quota}


def require_admin_user(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    return user


def _run_owner_filter(user: dict) -> str:
    auth = get_auth_manager()
    if not auth.has_users() or user.get("role") == "admin":
        return ""
    return str(user.get("user_id") or "")


def _ensure_run_access(run_id: str, user: dict) -> dict:
    try:
        detail = get_run_manager().get_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    owner_user_id = _run_owner_filter(user)
    if owner_user_id and detail.get("owner", {}).get("user_id") != owner_user_id:
        raise HTTPException(status_code=404, detail="run not found")
    return detail


def _forbid_legacy_run_without_owner(user: dict, detail: dict) -> None:
    if _run_owner_filter(user) and not detail.get("owner", {}).get("user_id"):
        raise HTTPException(status_code=404, detail="run not found")


def get_run_index() -> RunIndex:
    global _run_index
    if _run_index is None:
        _run_index = RunIndex(settings.db_path)
    return _run_index


def get_usage_tracker() -> UsageTracker:
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker(settings.db_path, settings.plan, settings.run_quota)
    return _usage_tracker


def require_api_token(x_api_token: str | None = Header(default=None)) -> None:
    if settings.api_token and x_api_token != settings.api_token:
        raise HTTPException(status_code=401, detail="valid X-API-Token required")

def get_adapter() -> WorldCupEngineAdapter:
    return WorldCupEngineAdapter(settings)


def get_skill_bridge() -> SkillBridge:
    return SkillBridge(settings.skill_path)


def get_run_manager() -> RunManager:
    global _run_manager
    if _run_manager is None:
        _run_manager = RunManager(settings.runs_path, auto_recover=True)
    return _run_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    assert_safe_external_binding(settings)
    manager = get_run_manager()
    manager.recover_pending_runs()
    manager.rebuild_index()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=resource_path("app", "static")), name="static")
templates = Jinja2Templates(directory=resource_path("app", "templates"))


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/desktop/settings/api-keys/"):
        return JSONResponse(status_code=422, content={"detail": "invalid desktop api key settings request"})
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    adapter = get_adapter()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "matches": adapter.list_matches(),
            "skill_available": settings.skill_path.exists(),
            "desktop_mode": settings.desktop_mode,
        },
    )


@app.get("/api/matches")
def api_matches():
    return {"matches": get_adapter().list_matches()}


@app.post("/api/generate")
def api_generate(payload: GenerateRequest):
    try:
        return get_adapter().generate_report(payload.match_id, payload.theme)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/skill/status")
def api_skill_status():
    return get_skill_bridge().describe()


@app.get("/api/system/doctor")
def api_system_doctor():
    return build_runtime_report()


@app.get("/api/system/setup-guide")
def api_system_setup_guide():
    return build_setup_guide(settings)


@app.get("/api/desktop/settings/api-keys/{provider:path}", dependencies=[Depends(require_desktop_mode)])
def api_desktop_get_api_key(provider: str):
    valid_provider = _valid_desktop_provider(provider)
    try:
        return get_desktop_api_key_store().get(valid_provider)
    except ApiKeyStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="desktop api key settings are temporarily unavailable") from exc


@app.put("/api/desktop/settings/api-keys/{provider:path}", dependencies=[Depends(require_desktop_mode)])
def api_desktop_put_api_key(provider: str, payload: DesktopApiKeyUpdateRequest):
    valid_provider = _valid_desktop_provider(provider)
    try:
        return get_desktop_api_key_store().put(valid_provider, payload.api_key)
    except ApiKeyStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="desktop api key settings are temporarily unavailable") from exc


@app.delete("/api/desktop/settings/api-keys/{provider:path}", dependencies=[Depends(require_desktop_mode)])
def api_desktop_delete_api_key(provider: str):
    valid_provider = _valid_desktop_provider(provider)
    try:
        return get_desktop_api_key_store().delete(valid_provider)
    except ApiKeyStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="desktop api key settings are temporarily unavailable") from exc


@app.get("/api/desktop/data-status")
def api_desktop_data_status():
    require_desktop_mode()
    return build_desktop_data_status(
        settings=settings,
        bridge=get_skill_bridge(),
        key_status=get_desktop_api_key_store().get("the_odds_api"),
        public_probe=_public_probe_tracker.snapshot(),
    )


@app.post("/api/odds/fetch")
def api_odds_fetch(payload: OddsFetchRequest):
    service = SportteryService(get_skill_bridge())
    nums = service.parse_nums(payload.nums) if isinstance(payload.nums, str) else payload.nums
    out_path = Path(payload.out_path) if payload.out_path else None
    try:
        command = service.build_fetch_odds_command(nums, out_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.dry_run:
        return {"dry_run": True, "parsed_nums": nums, "command": command}
    result = service.fetch_odds(nums, out=out_path)
    result["dry_run"] = False
    result["parsed_nums"] = nums
    return result


@app.post("/api/odds/inspect")
def api_odds_inspect(payload: OddsInspectRequest):
    odds_path = Path(payload.odds_path)
    try:
        resolved_path = odds_path.expanduser().resolve()
    except OSError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not _is_allowed_read_path(resolved_path):
        raise HTTPException(status_code=422, detail="odds_path must be inside project directory or /tmp")
    if not resolved_path.exists():
        raise HTTPException(status_code=404, detail="odds file not found")
    loaded = load_odds_file(resolved_path)
    if "_load_error" in loaded:
        health = inspect_odds_payload(loaded)
        raise HTTPException(status_code=422, detail=health)
    return inspect_odds_payload(loaded)


@app.post("/api/odds/discover")
def api_odds_discover(payload: OddsDiscoverRequest):
    service = SportteryService(get_skill_bridge())
    nums = service.parse_nums(payload.nums) if isinstance(payload.nums, str) else payload.nums
    timeout = payload.timeout if payload.timeout is not None else settings.default_command_timeout
    with tempfile.TemporaryDirectory(prefix="wc-odds-discover-") as tmp_dir:
        odds_path = Path(tmp_dir) / "odds.json"
        try:
            result = service.fetch_odds(nums, out=odds_path, timeout=timeout)
            if result.get("ok") is not True:
                safe_fetch = _safe_fetch_result(result) if settings.desktop_mode else result
                response_payload = {
                    "ok": False,
                    "valid_nums": [],
                    "invalid": {},
                    "markets": {},
                    "summary": "odds availability check failed before health inspection.",
                    "error": _safe_fetch_error(result) if settings.desktop_mode else result.get("error") or {"code": "fetch_failed", "message": "fetch_odds failed"},
                    "fetch": safe_fetch,
                }
                _record_public_probe_if_desktop(False, nums, response_payload)
                return response_payload
            health = inspect_odds_payload(load_odds_file(odds_path))
            safe_fetch = _safe_fetch_result(result) if settings.desktop_mode else result
            response_payload = {
                "ok": health["ok"],
                "valid_nums": health["valid_nums"],
                "invalid": health["invalid"],
                "markets": health["markets"],
                "summary": health["summary"],
                "health": health,
                "fetch": safe_fetch,
            }
            _record_public_probe_if_desktop(bool(health["ok"]), nums, response_payload)
            return response_payload
        except Exception as exc:
            response_payload = {
                "ok": False,
                "valid_nums": [],
                "invalid": {},
                "markets": {},
                "summary": "odds availability check failed before health inspection.",
                "error": (
                    {"code": "discover_error", "message": "odds availability check failed before health inspection"}
                    if settings.desktop_mode
                    else {"code": "discover_error", "type": exc.__class__.__name__, "message": str(exc)}
                ),
            }
            _record_public_probe_if_desktop(False, nums, response_payload)
            return response_payload


@app.post("/api/reports/build")
def api_reports_build(payload: ReportBuildRequest):
    service = ReportService(get_skill_bridge())
    odds_path = Path(payload.odds_path)
    out_path = Path(payload.out_path)
    intel_path = Path(payload.intel_path) if payload.intel_path else None
    try:
        command = service.build_report_command(
            odds_path=odds_path,
            out_path=out_path,
            title=payload.title,
            theme=payload.theme,
            intel_path=intel_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.dry_run:
        return {"dry_run": True, "command": command}
    result = service.generate_report_file(
        odds_path=odds_path,
        out_path=out_path,
        title=payload.title,
        theme=payload.theme,
        intel_path=intel_path,
    )
    result["dry_run"] = False
    return result


@app.post("/api/runs")
def api_runs_create(payload: RunCreateRequest, user: dict = Depends(current_user)):
    service = SportteryService(get_skill_bridge())
    nums = service.parse_nums(payload.nums) if isinstance(payload.nums, str) else payload.nums
    usage = get_usage_tracker()
    auth = get_auth_manager()
    try:
        if not payload.dry_run:
            if auth.has_users():
                auth.assert_can_create_real_run(user)
            else:
                usage.assert_can_create_real_run()
        result = get_run_manager().create_run(
            nums=nums,
            title=payload.title,
            theme=payload.theme,
            dry_run=payload.dry_run,
            background=payload.background,
            timeout=payload.timeout,
            owner_user_id=user.get("user_id", "") if auth.has_users() else "",
            owner_username=user.get("username", "") if auth.has_users() else "",
        )
        event_type = "dry_run_created" if payload.dry_run else "real_run_created"
        usage.record(event_type, result.get("run_id", ""), f"user={user.get('username')}")
        if auth.has_users():
            auth.record_usage(user["user_id"], event_type, result.get("run_id", ""), "api_runs_create")
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/runs")
def api_runs_list(status: str = "", num: str = "", quality: str = "", q: str = "", user: dict = Depends(current_user)):
    manager = get_run_manager()
    owner_user_id = _run_owner_filter(user)
    if status or num or quality or q:
        return {"runs": manager.search_runs(status=status, num=num, quality=quality, q=q, owner_user_id=owner_user_id)}
    return {"runs": manager.list_runs(owner_user_id=owner_user_id)}


@app.post("/api/runs/recover")
def api_runs_recover():
    return get_run_manager().recover_pending_runs()


@app.get("/api/runs/queue")
def api_runs_queue():
    return get_run_manager().queue_stats()


@app.get("/api/runs/failures")
def api_runs_failures():
    return get_run_manager().failure_dashboard()


@app.get("/api/runs/{run_id}")
def api_runs_detail(run_id: str, user: dict = Depends(current_user)):
    return _ensure_run_access(run_id, user)


@app.post("/api/runs/{run_id}/retry")
def api_runs_retry(run_id: str, user: dict = Depends(current_user)):
    try:
        detail = _ensure_run_access(run_id, user)
        _forbid_legacy_run_without_owner(user, detail)
        return get_run_manager().retry_run(run_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 422 if "invalid run_id" in message else 409
        raise HTTPException(status_code=status_code, detail=message) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc


@app.post("/api/runs/{run_id}/cancel")
def api_runs_cancel(run_id: str, user: dict = Depends(current_user)):
    try:
        detail = _ensure_run_access(run_id, user)
        _forbid_legacy_run_without_owner(user, detail)
        return get_run_manager().cancel_run(run_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 422 if "invalid run_id" in message else 409
        raise HTTPException(status_code=status_code, detail=message) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc


@app.get("/api/runs/{run_id}/odds-health")
def api_runs_odds_health(run_id: str, user: dict = Depends(current_user)):
    try:
        _ensure_run_access(run_id, user)
        health = get_run_manager().odds_health(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    if health is None:
        raise HTTPException(status_code=404, detail="odds health not found")
    return health


@app.get("/api/runs/{run_id}/prediction")
def api_runs_prediction(run_id: str, user: dict = Depends(current_user)):
    try:
        _ensure_run_access(run_id, user)
        prediction = get_run_manager().prediction(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    if prediction is None:
        raise HTTPException(status_code=404, detail="prediction not found")
    return prediction


@app.get("/api/runs/{run_id}/export.zip")
def api_runs_export(run_id: str, user: dict = Depends(current_user)):
    try:
        _ensure_run_access(run_id, user)
        payload = get_run_manager().export_zip(run_id)
        get_usage_tracker().record("export_zip", run_id, "api_runs_export")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{run_id}-export.zip"'},
    )


@app.get("/runs/{run_id}/report.html")
def run_report_file(run_id: str, user: dict = Depends(current_user)):
    try:
        _ensure_run_access(run_id, user)
        report_path = get_run_manager().report_file(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if report_path is None:
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(report_path, media_type="text/html")


@app.get("/api/me")
def api_me(user: dict = Depends(current_user)):
    quota = get_auth_manager().quota_status(user) if get_auth_manager().has_users() else get_usage_tracker().quota_status()
    return {"user": user, "quota": quota}


@app.post("/api/admin/users")
def api_admin_create_user(payload: UserCreateRequest, admin: dict = Depends(require_admin_user)):
    try:
        return get_auth_manager().create_user(
            username=payload.username,
            role=payload.role,
            plan=payload.plan,
            run_quota=payload.run_quota,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/admin/users")
def api_admin_users(admin: dict = Depends(require_admin_user)):
    return get_auth_manager().summary()


@app.patch("/api/admin/users/{user_id}")
def api_admin_update_user(user_id: str, payload: UserUpdateRequest, admin: dict = Depends(require_admin_user)):
    try:
        return get_auth_manager().update_user(
            user_id,
            role=payload.role,
            plan=payload.plan,
            run_quota=payload.run_quota,
            active=payload.active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/admin/users/{user_id}/reset-token")
def api_admin_reset_user_token(user_id: str, admin: dict = Depends(require_admin_user)):
    try:
        return get_auth_manager().reset_token(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/admin/usage")
def api_admin_usage(admin: dict = Depends(require_admin_user)):
    return get_usage_tracker().summary()


@app.get("/api/admin/run-index")
def api_admin_run_index(admin: dict = Depends(require_admin_user)):
    return get_run_index().stats()


@app.post("/api/admin/run-index/rebuild")
def api_admin_run_index_rebuild(admin: dict = Depends(require_admin_user)):
    return get_run_manager().rebuild_index()


@app.get("/report/{match_id}", response_class=HTMLResponse)
def report_page(request: Request, match_id: str, theme: str = "light"):
    try:
        report = get_adapter().generate_report(match_id, theme)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "report.html",
        {"app_name": settings.app_name, "report": report, "theme": theme},
    )


def _is_allowed_read_path(path: Path) -> bool:
    allowed_roots = [
        ROOT_DIR.resolve(),
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
    ]
    return any(path == root or root in path.parents for root in allowed_roots)


def _safe_fetch_result(result: dict) -> dict:
    allowed = ("ok", "returncode", "duration_seconds")
    return {key: result[key] for key in allowed if key in result}


def _safe_fetch_error(result: dict) -> dict:
    error = result.get("error") if isinstance(result, dict) else None
    code = error.get("code") if isinstance(error, dict) else "fetch_failed"
    return {"code": code or "fetch_failed", "message": "odds availability check failed"}


def _record_public_probe_if_desktop(ok: bool, nums: list[str], payload: dict) -> None:
    if settings.desktop_mode:
        _public_probe_tracker.record_discover(ok=ok, nums=nums, payload=payload)
