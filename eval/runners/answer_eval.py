"""
Answer-faithfulness evaluation via ragas (build plan A2 §8 Day 23).

Metric: faithfulness — fraction of answer claims that are supported by
the retrieved context. ≥ 0.80 is the v1 target.

ragas pulls langchain + datasets transitively; that's why eval has its
own requirements.txt. Don't add ragas to backend/requirements.txt — the
HF Spaces image stays slim.

For Day 23 this is a thin wrapper around `ragas.metrics.Faithfulness`.
Day 33 prompt-iteration runner reuses this without changes.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.db.supabase import admin_client
from app.services.rag import stream_rag_answer

from .loader import GoldenItem

logger = logging.getLogger(__name__)


@dataclass
class FaithfulnessRow:
    item_id: str
    faithfulness: float


@dataclass
class FaithfulnessReport:
    n: int
    mean_faithfulness: float
    rows: list[FaithfulnessRow]

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "mean_faithfulness": self.mean_faithfulness,
            "rows": [r.__dict__ for r in self.rows],
        }


async def _faithfulness_score(answer: str, contexts: list[str]) -> float:
    """
    Single-shot ragas faithfulness call. Lazy-imports ragas so the module
    can be imported in CI environments without ragas installed (the runner
    will then short-circuit and return 0.0).
    """
    try:
        from ragas import EvaluationDataset, evaluate  # type: ignore[import]
        from ragas.metrics import Faithfulness  # type: ignore[import]
    except ImportError:
        logger.warning("ragas not installed — faithfulness=0.0 placeholder")
        return 0.0

    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": "",  # the metric uses answer + context only
                "response": answer,
                "retrieved_contexts": contexts,
            }
        ]
    )
    result = evaluate(dataset, metrics=[Faithfulness()])
    score = result.scores[0].get("faithfulness", 0.0)
    return float(score)


async def evaluate_faithfulness(
    items: list[GoldenItem],
    doc_id_by_path: dict[str, str],
    *,
    user_id: str,
) -> FaithfulnessReport:
    db = admin_client()
    rows: list[FaithfulnessRow] = []

    for item in items:
        doc_id = doc_id_by_path.get(item.doc_path)
        if not doc_id:
            continue

        answer = ""
        contexts: list[str] = []
        async for ev in stream_rag_answer(db, user_id, doc_id, item.question):
            if ev["event"] == "answer":
                answer = ev["answer"]
            elif ev["event"] == "done":
                # Reuse the same lookup pattern as citation_eval: fetch chunk
                # texts via storage. For ragas we just need plain text contexts.
                contexts = _resolve_contexts(db, ev["retrieved_chunks"])

        if not answer or not contexts:
            rows.append(FaithfulnessRow(item_id=item.id, faithfulness=0.0))
            continue

        score = await _faithfulness_score(answer, contexts)
        rows.append(FaithfulnessRow(item_id=item.id, faithfulness=score))

    if not rows:
        return FaithfulnessReport(n=0, mean_faithfulness=0.0, rows=[])
    mean = sum(r.faithfulness for r in rows) / len(rows)
    return FaithfulnessReport(n=len(rows), mean_faithfulness=mean, rows=rows)


def _resolve_contexts(db, retrieved_chunks: list[dict]) -> list[str]:
    import json
    from app.services import storage

    if not retrieved_chunks:
        return []
    ids = [c["id"] for c in retrieved_chunks]
    res = (
        db.table("document_chunks")
        .select("id, text_storage_path, chunk_index")
        .in_("id", ids)
        .execute()
    )
    paths_seen: dict[str, dict[int, str]] = {}
    out: list[str] = []
    for row in res.data or []:
        p = row["text_storage_path"]
        if p not in paths_seen:
            blob = storage.download(db, storage.BUCKET_CHUNKS, p)
            paths_seen[p] = {
                c["chunk_index"]: c["text"]
                for c in json.loads(blob.decode("utf-8"))
            }
        text = paths_seen[p].get(row["chunk_index"], "")
        if text:
            out.append(text)
    return out
