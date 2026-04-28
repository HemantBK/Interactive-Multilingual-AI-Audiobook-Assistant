"""
ARIA Backend — FastAPI entry point.

Day 22: Sentry init runs at module import (before FastAPI app creation)
so Sentry can patch starlette/fastapi internals. Day 18 KILL_SWITCH
middleware + slowapi rate limits stay wired.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import auth as auth_api
from app.api import documents as documents_api
from app.api import rag as rag_api
from app.api import translate as translate_api
from app.api import tts as tts_api
from app.core.config import settings
from app.core.limiter import limiter
from app.core.observability import init_sentry
from app.db.supabase import admin_client
from app.middleware import kill_switch
from app.services.prompt_registry import ensure_prompt_registered
from app.services.prompts import PROMPT_ID, PROMPT_VERSION, SYSTEM_PROMPT

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("aria")

# Sentry init must happen BEFORE app/route construction so the FastAPI
# integration can monkey-patch the framework. No-op when DSN absent.
init_sentry()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.supabase_url and settings.supabase_service_key:
        try:
            ensure_prompt_registered(
                admin_client(),
                prompt_id=PROMPT_ID,
                version=PROMPT_VERSION,
                content=SYSTEM_PROMPT,
                description="Day 9 baseline — RAG system prompt with structured citations",
            )
        except Exception:  # noqa: BLE001
            logger.exception("prompt registration failed at startup")
    else:
        logger.warning("Supabase not configured — skipping prompt registration")
    yield


app = FastAPI(
    title="ARIA API",
    version="0.1.0",
    description="Multilingual AI audiobook + RAG with precise citations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
kill_switch.install(app)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_api.router)
app.include_router(documents_api.router)
app.include_router(rag_api.router)
app.include_router(translate_api.router)
app.include_router(tts_api.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aria-api",
        "version": app.version,
        "env": settings.app_env,
        "kill_switch": "on" if settings.kill_switch else "off",
    }


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"message": "ARIA API. See /docs for OpenAPI."}
