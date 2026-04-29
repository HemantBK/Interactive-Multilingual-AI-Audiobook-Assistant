"""
Groq Llama 3.3 70B streaming client (build plan §3, §11).

Reliability layers (innermost → outermost):
  1. Tenacity retries — 1 try + 2 retries, 0.5 s / 1 s / 2 s exponential.
     Only retries TransientError types (connection, rate-limit, timeout).
     4xx auth/validation errors are not retried.
  2. AsyncCircuitBreaker — opens after 5 consecutive failures, half-opens
     after 60 s. Prevents thundering herd against a sick provider.

Stream semantics: retries cover the INITIAL connect call only. Once we
start consuming the stream, we cannot replay — so we don't.

Token usage capture (Day 9): pass `capture_usage={}` and the dict is
populated when the final `usage` chunk arrives. Requires
stream_options={"include_usage": True}.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from groq import APIConnectionError, APIError, AsyncGroq, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.services.circuit_breaker import AsyncCircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIMEOUT_SECONDS = 30.0

_client: AsyncGroq | None = None
_breaker = AsyncCircuitBreaker(fail_threshold=5, reset_seconds=60.0)


class GroqUnavailableError(Exception):
    """Surfaces both circuit-open and unrecoverable transport errors to callers."""


def _client_singleton() -> AsyncGroq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise GroqUnavailableError("GROQ_API_KEY is not configured")
        _client = AsyncGroq(
            api_key=settings.groq_api_key, timeout=DEFAULT_TIMEOUT_SECONDS
        )
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception_type(
        (APIConnectionError, RateLimitError, TimeoutError)
    ),
    reraise=True,
)
async def _connect_stream(
    *,
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    response_format: dict[str, Any] | None,
    include_usage: bool,
):
    client = _client_singleton()
    kwargs: dict[str, Any] = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    if response_format is not None:
        kwargs["response_format"] = response_format
    if include_usage:
        kwargs["stream_options"] = {"include_usage": True}
    return await client.chat.completions.create(**kwargs)


async def groq_stream_chat(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    response_format: dict[str, Any] | None = None,
    capture_usage: dict[str, int] | None = None,
) -> AsyncIterator[str]:
    """
    Yield content tokens as Groq streams them. If `capture_usage` is provided,
    the dict is populated with prompt_tokens, completion_tokens, total_tokens
    when the final stream chunk arrives.
    """
    include_usage = capture_usage is not None

    async def _do_connect():
        return await _connect_stream(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
            include_usage=include_usage,
        )

    try:
        stream = await _breaker.call(_do_connect)
    except CircuitOpenError as exc:
        raise GroqUnavailableError(str(exc)) from exc
    except APIError as exc:
        # Auth / quota / 4xx — no retry, surface to caller.
        raise GroqUnavailableError(f"Groq API error: {exc}") from exc

    async for chunk in stream:
        # Usage chunks have no choices; capture and continue.
        if capture_usage is not None and getattr(chunk, "usage", None):
            usage = chunk.usage
            capture_usage["prompt_tokens"] = getattr(usage, "prompt_tokens", 0) or 0
            capture_usage["completion_tokens"] = (
                getattr(usage, "completion_tokens", 0) or 0
            )
            capture_usage["total_tokens"] = getattr(usage, "total_tokens", 0) or 0
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content
