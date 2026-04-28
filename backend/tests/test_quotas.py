"""Per-user daily quotas — supabase client is mocked since the rule logic
is what we care about, not the round-trip."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services import quotas
from app.services.quotas import (
    CAP_BY_COUNTER,
    QuotaExceededError,
    assert_under_cap,
    bump,
)


def _mock_db_with_value(counter: str, current: int) -> MagicMock:
    """Build a chain mock that returns {counter: current} when read."""
    db = MagicMock()
    chain = (
        db.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .limit.return_value
    )
    chain.execute.return_value = MagicMock(
        data=[{counter: current}] if current is not None else []
    )
    return db


# ---------- assert_under_cap ----------


def test_passes_when_under_cap() -> None:
    db = _mock_db_with_value("rag_queries", 100)
    assert_under_cap(db, user_id="u", counter="rag_queries", delta=1, cap=500)


def test_passes_at_exactly_one_below_cap() -> None:
    db = _mock_db_with_value("rag_queries", 499)
    # 499 + 1 = 500 (cap) — not exceeded
    assert_under_cap(db, user_id="u", counter="rag_queries", delta=1, cap=500)


def test_raises_at_cap_with_increment() -> None:
    db = _mock_db_with_value("rag_queries", 500)
    with pytest.raises(QuotaExceededError) as exc:
        assert_under_cap(db, user_id="u", counter="rag_queries", delta=1, cap=500)
    assert exc.value.status_code == 429


def test_raises_well_above_cap() -> None:
    db = _mock_db_with_value("documents_uploaded", 50)
    with pytest.raises(QuotaExceededError):
        assert_under_cap(db, user_id="u", counter="documents_uploaded", delta=1, cap=10)


def test_treats_missing_row_as_zero() -> None:
    db = _mock_db_with_value("tts_chars", None)  # no rows → []
    # Should NOT raise — current=0 + delta=1000 ≤ cap 100000
    assert_under_cap(db, user_id="u", counter="tts_chars", delta=1000, cap=100_000)


def test_uses_default_cap_when_none() -> None:
    db = _mock_db_with_value("rag_queries", CAP_BY_COUNTER["rag_queries"])
    with pytest.raises(QuotaExceededError):
        assert_under_cap(db, user_id="u", counter="rag_queries", delta=1)


def test_tts_chars_uses_text_length_as_delta() -> None:
    db = _mock_db_with_value("tts_chars", 99_999)
    # Try to add 2 chars when only 1 is left
    with pytest.raises(QuotaExceededError):
        assert_under_cap(db, user_id="u", counter="tts_chars", delta=2, cap=100_000)


# ---------- bump ----------


def test_bump_calls_rpc_with_expected_args(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()
    db.rpc.return_value.execute.return_value = MagicMock(data=11)

    new_value = bump(db, user_id="u-1", counter="documents_uploaded", delta=1)

    assert new_value == 11
    db.rpc.assert_called_once_with(
        "bump_user_usage",
        {"p_user_id": "u-1", "p_counter": "documents_uploaded", "p_delta": 1},
    )


def test_bump_swallows_failure_and_returns_zero() -> None:
    db = MagicMock()
    db.rpc.return_value.execute.side_effect = RuntimeError("network down")

    # Bookkeeping must never break the user-facing path.
    result = bump(db, user_id="u-1", counter="rag_queries", delta=1)
    assert result == 0


# ---------- defaults wired correctly ----------


def test_caps_loaded_from_settings() -> None:
    # Sanity: caps come from settings — defaults from .env.example.
    assert CAP_BY_COUNTER["documents_uploaded"] >= 1
    assert CAP_BY_COUNTER["rag_queries"] >= 1
    assert CAP_BY_COUNTER["tts_chars"] >= 1
