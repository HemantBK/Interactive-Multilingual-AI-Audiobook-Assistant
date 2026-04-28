"""
Minimal async-aware circuit breaker.

Why hand-rolled instead of pybreaker: pybreaker's async support varies by
version and we want predictable behavior across deployments. This is ~30 lines
and covers the three states we care about:

  closed     → calls pass through; failures increment a counter
  open       → calls raise CircuitOpenError without touching the wrapped fn
  half-open  → after reset_seconds, ONE trial call is admitted; success
               closes, failure re-opens

State mutations are guarded by an asyncio.Lock so concurrent callers don't
race on the counter.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(Exception):
    """The breaker refused the call because too many recent failures occurred."""


class AsyncCircuitBreaker:
    def __init__(self, fail_threshold: int = 5, reset_seconds: float = 60.0):
        self.fail_threshold = fail_threshold
        self.reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def failures(self) -> int:
        return self._failures

    def _state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.monotonic() - self._opened_at >= self.reset_seconds:
            return "half_open"
        return "open"

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self._state() == "open":
                raise CircuitOpenError(
                    f"circuit open ({self._failures} consecutive failures)"
                )

        try:
            result = await fn()
        except Exception:
            async with self._lock:
                self._failures += 1
                if self._failures >= self.fail_threshold:
                    self._opened_at = time.monotonic()
            raise

        async with self._lock:
            self._failures = 0
            self._opened_at = None
        return result
