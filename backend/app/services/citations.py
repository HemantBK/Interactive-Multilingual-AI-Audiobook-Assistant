"""
Citation validation (build plan §2 — "Backend validates citations actually
exist in retrieved chunks").

A citation is valid iff:
  1. chunk_id is an int that appears in the retrieved-chunks set we passed
     to the model (it cannot cite a chunk it never saw).
  2. quote is a non-empty substring of that chunk's text. The substring
     check has a whitespace-normalised fallback so trivial reformatting
     (e.g. line breaks → spaces) by the model doesn't drop legitimate cites.

Dropped citations are returned alongside valid ones with a 'reason' field —
caller logs them but does not surface to the user.
"""

from __future__ import annotations

from typing import Any


def validate_citations(
    raw_citations: list[Any],
    retrieved_chunks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (valid, dropped). Each valid entry: {chunk_id: int, quote: str}."""
    retrieved_ids = {c["id"] for c in retrieved_chunks}
    text_by_id = {c["id"]: c.get("text", "") for c in retrieved_chunks}

    valid: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []

    for raw in raw_citations:
        if not isinstance(raw, dict):
            dropped.append({"raw": str(raw)[:80], "reason": "not_object"})
            continue

        try:
            chunk_id = int(raw.get("chunk_id"))
        except (TypeError, ValueError):
            dropped.append({"raw_chunk_id": raw.get("chunk_id"), "reason": "bad_chunk_id"})
            continue

        quote = str(raw.get("quote", "")).strip()
        if not quote:
            dropped.append({"chunk_id": chunk_id, "reason": "empty_quote"})
            continue

        if chunk_id not in retrieved_ids:
            dropped.append(
                {"chunk_id": chunk_id, "quote": quote[:80], "reason": "chunk_id_not_in_set"}
            )
            continue

        chunk_text = text_by_id.get(chunk_id, "")
        # Fallback: normalise whitespace before declaring failure.
        if quote not in chunk_text and " ".join(quote.split()) not in " ".join(
            chunk_text.split()
        ):
            dropped.append(
                {
                    "chunk_id": chunk_id,
                    "quote": quote[:80],
                    "reason": "quote_not_substring",
                }
            )
            continue

        valid.append({"chunk_id": chunk_id, "quote": quote})

    return valid, dropped
