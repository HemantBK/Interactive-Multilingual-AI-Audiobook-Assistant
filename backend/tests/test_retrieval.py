"""Retrieval helper — pure-function tests."""

from __future__ import annotations

from app.services.retrieval import _format_embedding


def test_format_embedding_basic() -> None:
    out = _format_embedding([1.0, 2.5, -3.25])
    assert out.startswith("[") and out.endswith("]")
    parts = out[1:-1].split(",")
    assert len(parts) == 3


def test_format_embedding_preserves_precision() -> None:
    vec = [0.123456789, -0.987654321]
    out = _format_embedding(vec)
    # 7-digit precision is enough for halfvec (16-bit float)
    assert "0.1234567" in out
    assert "-0.9876543" in out


def test_format_embedding_round_trips_for_pgvector_syntax() -> None:
    out = _format_embedding([0.0, 1.0])
    assert out == "[0.0000000,1.0000000]"
