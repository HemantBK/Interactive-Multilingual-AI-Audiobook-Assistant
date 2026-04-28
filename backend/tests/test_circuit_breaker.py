"""Async circuit breaker — open/half-open/close transitions."""

from __future__ import annotations

import asyncio
import time

import pytest

from app.services.circuit_breaker import AsyncCircuitBreaker, CircuitOpenError


@pytest.mark.asyncio
async def test_closed_allows_calls() -> None:
    cb = AsyncCircuitBreaker(fail_threshold=3, reset_seconds=60)

    async def ok() -> int:
        return 42

    assert await cb.call(ok) == 42
    assert cb.failures == 0


@pytest.mark.asyncio
async def test_failures_increment_until_open() -> None:
    cb = AsyncCircuitBreaker(fail_threshold=3, reset_seconds=60)

    async def boom() -> None:
        raise RuntimeError("boom")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb.call(boom)

    assert cb.failures == 3

    async def whatever() -> int:
        return 1

    with pytest.raises(CircuitOpenError):
        await cb.call(whatever)


@pytest.mark.asyncio
async def test_success_resets_counter() -> None:
    cb = AsyncCircuitBreaker(fail_threshold=3, reset_seconds=60)

    async def boom() -> None:
        raise RuntimeError("boom")

    async def ok() -> int:
        return 1

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(boom)
    assert cb.failures == 2

    assert await cb.call(ok) == 1
    assert cb.failures == 0


@pytest.mark.asyncio
async def test_half_open_after_reset_window() -> None:
    cb = AsyncCircuitBreaker(fail_threshold=2, reset_seconds=0.05)

    async def boom() -> None:
        raise RuntimeError("boom")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(boom)

    # Immediately after opening, calls are refused.
    async def ok() -> int:
        return 7

    with pytest.raises(CircuitOpenError):
        await cb.call(ok)

    # After the reset window, the breaker admits one trial. Success closes it.
    await asyncio.sleep(0.07)
    assert await cb.call(ok) == 7
    assert cb.failures == 0
