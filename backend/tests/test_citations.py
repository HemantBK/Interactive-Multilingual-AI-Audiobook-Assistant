"""Citation validation — pure-function tests."""

from __future__ import annotations

from app.services.citations import validate_citations


def _retrieved(items: list[tuple[int, str]]) -> list[dict]:
    return [{"id": cid, "text": t} for cid, t in items]


def test_passes_real_substring() -> None:
    retrieved = _retrieved([(1, "Photosynthesis converts sunlight to chemical energy.")])
    raw = [{"chunk_id": 1, "quote": "Photosynthesis converts sunlight"}]
    valid, dropped = validate_citations(raw, retrieved)
    assert len(valid) == 1
    assert valid[0] == {"chunk_id": 1, "quote": "Photosynthesis converts sunlight"}
    assert dropped == []


def test_drops_unknown_chunk_id() -> None:
    retrieved = _retrieved([(1, "x")])
    raw = [{"chunk_id": 999, "quote": "x"}]
    valid, dropped = validate_citations(raw, retrieved)
    assert valid == []
    assert dropped[0]["reason"] == "chunk_id_not_in_set"


def test_drops_quote_not_in_chunk() -> None:
    retrieved = _retrieved([(1, "Photosynthesis is a plant process.")])
    raw = [{"chunk_id": 1, "quote": "Aristotle wrote about photosynthesis."}]
    valid, dropped = validate_citations(raw, retrieved)
    assert valid == []
    assert dropped[0]["reason"] == "quote_not_substring"


def test_normalises_whitespace_in_quote() -> None:
    retrieved = _retrieved([(1, "Photosynthesis converts\nsunlight\tto energy.")])
    raw = [{"chunk_id": 1, "quote": "Photosynthesis converts sunlight to energy"}]
    valid, dropped = validate_citations(raw, retrieved)
    assert len(valid) == 1
    assert dropped == []


def test_coerces_string_chunk_id() -> None:
    retrieved = _retrieved([(7, "Some text content here.")])
    raw = [{"chunk_id": "7", "quote": "Some text content"}]
    valid, dropped = validate_citations(raw, retrieved)
    assert len(valid) == 1
    assert valid[0]["chunk_id"] == 7  # coerced int


def test_drops_malformed_entries() -> None:
    retrieved = _retrieved([(1, "x")])
    raw = [
        {"chunk_id": "abc", "quote": "x"},  # bad_chunk_id
        {},                                  # bad_chunk_id (None)
        "garbage",                           # not_object
        [1, 2, 3],                           # not_object
    ]
    valid, dropped = validate_citations(raw, retrieved)
    assert valid == []
    reasons = {d["reason"] for d in dropped}
    assert "bad_chunk_id" in reasons
    assert "not_object" in reasons


def test_drops_empty_quote() -> None:
    retrieved = _retrieved([(1, "valid text")])
    raw = [{"chunk_id": 1, "quote": ""}]
    valid, dropped = validate_citations(raw, retrieved)
    assert valid == []
    assert dropped[0]["reason"] == "empty_quote"


def test_handles_empty_input() -> None:
    valid, dropped = validate_citations([], [])
    assert valid == []
    assert dropped == []


def test_drops_whitespace_only_quote() -> None:
    retrieved = _retrieved([(1, "valid text here")])
    raw = [{"chunk_id": 1, "quote": "   \n\t  "}]
    valid, dropped = validate_citations(raw, retrieved)
    assert valid == []
    assert dropped[0]["reason"] == "empty_quote"


def test_indic_quote_substring_passes() -> None:
    chunk = "नमस्ते दुनिया, यह एक हिंदी पाठ है।"
    retrieved = _retrieved([(42, chunk)])
    raw = [{"chunk_id": 42, "quote": "यह एक हिंदी पाठ है"}]
    valid, _ = validate_citations(raw, retrieved)
    assert len(valid) == 1
    assert valid[0]["chunk_id"] == 42
