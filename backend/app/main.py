"""
ARIA Backend — FastAPI entry point.

Day 1: only a health endpoint. Real routes land in Week 1 Day 3+.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth as auth_api
from app.core.config import settings

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("aria")


app = FastAPI(
    title="ARIA API",
    version="0.1.0",
    description="Multilingual AI audiobook + RAG with precise citations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_api.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aria-api",
        "version": app.version,
        "env": settings.app_env,
    }


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"message": "ARIA API. See /docs for OpenAPI."}
