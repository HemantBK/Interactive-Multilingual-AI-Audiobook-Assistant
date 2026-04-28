"""
Golden-set loader + validator (build plan A2 §8, Day 23).

Reads eval/datasets/golden_set.json and yields typed records. Validation
catches schema drift early — a renamed field in the JSON shouldn't
silently produce zeros across the metrics dashboard.

Set types map 1:1 to runners:
  retrieval     → eval/runners/retrieval_eval.py
  citation      → eval/runners/citation_eval.py
  answer        → eval/runners/answer_eval.py
  translation   → eval/runners/translation_eval.py (Day 23.1+ — not yet)
  tts           → manual MOS sheet (Day 23.1+ — not yet)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

SetType = Literal["retrieval", "citation", "answer", "translation", "tts"]


@dataclass(frozen=True)
class GoldenItem:
    id: str
    set: SetType
    language: str
    doc_path: str               # canonical path within the eval fixtures
    question: str
    expected_chunk_text_excerpt: str
    expected_page: int | None
    labeler: str | None
    labeled_at: str | None


REQUIRED_FIELDS = (
    "id",
    "set",
    "language",
    "question",
    "expected_chunk_text_excerpt",
)
ALLOWED_SETS: frozenset[str] = frozenset(
    ("retrieval", "citation", "answer", "translation", "tts")
)


class GoldenSetError(ValueError):
    """Schema / validation failure in the golden set file."""


def load(path: Path) -> list[GoldenItem]:
    """Parse and validate a golden_set.json file. Skips EXAMPLE-prefixed entries."""
    if not path.exists():
        raise GoldenSetError(f"golden set not found at {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))

    if "items" not in raw or not isinstance(raw["items"], list):
        raise GoldenSetError("golden set must have a top-level `items` array")

    out: list[GoldenItem] = []
    for i, entry in enumerate(raw["items"]):
        if not isinstance(entry, dict):
            raise GoldenSetError(f"item {i}: not an object")
        # Skip the template's example entry — keeps golden_set.json shippable
        # before any real labels exist without crashing the runner.
        if str(entry.get("id", "")).startswith("EXAMPLE-"):
            continue
        for field in REQUIRED_FIELDS:
            if field not in entry:
                raise GoldenSetError(f"item {i} ({entry.get('id', '?')}) missing field: {field}")
        if entry["set"] not in ALLOWED_SETS:
            raise GoldenSetError(
                f"item {entry['id']}: unknown set {entry['set']!r}; "
                f"must be one of {sorted(ALLOWED_SETS)}"
            )
        out.append(
            GoldenItem(
                id=entry["id"],
                set=entry["set"],
                language=entry.get("language", "en"),
                doc_path=entry.get("doc_path", ""),
                question=entry["question"],
                expected_chunk_text_excerpt=entry["expected_chunk_text_excerpt"],
                expected_page=entry.get("expected_page"),
                labeler=entry.get("labeler"),
                labeled_at=entry.get("labeled_at"),
            )
        )
    return out


def filter_by_set(items: list[GoldenItem], set_name: SetType) -> Iterator[GoldenItem]:
    return (it for it in items if it.set == set_name)
