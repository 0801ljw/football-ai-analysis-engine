"""Desktop session boundary; credentials arrive over the parent's private stdin pipe."""
from __future__ import annotations

import secrets
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

_session_token = ""


def install_session_token(token: str) -> None:
    global _session_token
    if not isinstance(token, str) or len(token) < 43:
        raise ValueError("invalid desktop session credential")
    _session_token = token


def session_token() -> str:
    return _session_token


async def desktop_boundary(request, call_next, settings):
    if not settings.desktop_mode:
        return await call_next(request)
    token = settings.desktop_session_token
    # No credential means no desktop service, including public shell resources.
    if len(token) < 43:
        return JSONResponse({"detail": "desktop session unavailable"}, status_code=503)
    host = request.headers.get("host", "")
    try:
        parsed = urlsplit("http://" + host)
        valid_host = (parsed.hostname == "127.0.0.1" and parsed.port is not None
                      and host == f"127.0.0.1:{parsed.port}")
    except ValueError:
        valid_host = False
    if not valid_host:
        return JSONResponse({"detail": "invalid desktop host"}, status_code=403)
    origin = request.headers.get("origin")
    if origin is not None and origin != f"http://{host}":
        return JSONResponse({"detail": "invalid desktop origin"}, status_code=403)
    if request.headers.get("sec-fetch-site") == "cross-site":
        return JSONResponse({"detail": "cross-site desktop request denied"}, status_code=403)
    public_shell = request.method in {"GET", "HEAD"} and (
        request.url.path == "/" or request.url.path.startswith("/static/")
    )
    if not public_shell and not secrets.compare_digest(
        request.headers.get("x-desktop-session", "").encode(), token.encode()
    ):
        return JSONResponse({"detail": "valid desktop session required"}, status_code=401)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response
