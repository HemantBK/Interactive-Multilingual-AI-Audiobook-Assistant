"""
KILL_SWITCH middleware (build plan A2 §6, §17, Day 18).

When `settings.kill_switch=True`, every AI / data-mutation endpoint
returns 503 immediately. Auth, /health, /, and read-only document GETs
keep working so users can sign in, see their existing docs, and reach
the support page even while AI is disabled.

The flag is read fresh per request so an operator can flip it via env
var on the running container — Day 22 may add a DB-backed live flag.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import settings

# Methods × path-prefix combinations that AI / mutation hits go through.
# /documents GET stays open so users can see what's already indexed.
_GATED_PREFIXES = ("/rag", "/tts", "/translate")
_GATED_PREFIXES_ANY_METHOD: tuple[str, ...] = _GATED_PREFIXES
_GATED_MUTATION_PREFIXES = ("/documents",)
_GATED_MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _is_gated(method: str, path: str) -> bool:
    if any(path == p or path.startswith(p + "/") or path == p for p in _GATED_PREFIXES_ANY_METHOD):
        return True
    if method in _GATED_MUTATION_METHODS and any(
        path == p or path.startswith(p + "/") for p in _GATED_MUTATION_PREFIXES
    ):
        return True
    return False


async def kill_switch_middleware(request: Request, call_next):
    if settings.kill_switch and _is_gated(request.method, request.url.path):
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "ARIA is temporarily disabled by the operator. "
                    "Please try again in a few minutes."
                ),
                "code": "kill_switch_active",
            },
        )
    return await call_next(request)


def install(app: ASGIApp) -> None:
    """Install the kill-switch middleware on a FastAPI app."""
    # Imported here to avoid pulling FastAPI at module load time.
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("kill_switch.install expects a FastAPI app")
    app.middleware("http")(kill_switch_middleware)
