"""
Retrieval evaluation: hit@k, MRR (build plan A2 §8 Day 23).

For each retrieval-set golden item:
  1. Embed question via bge-m3 (same model as production).
  2. search_chunks RPC against the labelled doc → top-K (default 20).
  3. Rerank top-K → top-5 (bge-reranker-v2-m3).
  4. Hit@5: does any returned chunk's text contain
     `expected_chunk_text_excerpt` (whitespace-normalised substring)?
  5. MRR (1-based reciprocal of position of first hit; 0 if no hit).

Imports from backend.app.services so the same code path runs in eval as in
production. Run with `PYTHONPATH=backend` or `python -m eval.runners.cli`
from the repo root after installing both requirements files.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.db.supabase import admin_client
from app.services import storage
from app.services.embedding import embed_texts
from app.services.rerank import rerank
from app.services.retrieval import retrieve_top_k

from .loader import GoldenItem

logger = logging.getLogger(__name__)

TOP_K_RETRIEVE = 20
TOP_K_RERANK = 5


@dataclass
class RetrievalRow:
    item_id: str
    language: str
    hit_at_5: bool
    mrr: float
    top5_pages: list[int]
    top5_scores: list[float]


@dataclass
class RetrievalReport:
    n: int
    hit_at_5: float
    mrr: float
    by_language: dict[str, dict[str, float]]
    rows: list[RetrievalRow]

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "hit_at_5": self.hit_at_5,
            "mrr": self.mrr,
            "by_language": self.by_language,
            "rows": [r.__dict__ for r in self.rows],
        }


def _norm_ws(s: str) -> str:
    return " ".join(s.split()).lower()


def _hit_index(top5_texts: list[str], expected_excerpt: str) -> int | None:
    needle = _norm_ws(expected_excerpt)
    if not needle:
        return None
    for i, txt in enumerate(top5_texts):
        if needle in _norm_ws(txt):
            return i
    return None


def evaluate_retrieval(
    items: list[GoldenItem],
    doc_id_by_path: dict[str, str],
) -> RetrievalReport:
    db = admin_client()
    rows: list[RetrievalRow] = []

    for item in items:
        doc_id = doc_id_by_path.get(item.doc_path)
        if not doc_id:
            logger.warning("skip %s: no document id mapped for %s", item.id, item.doc_path)
            continue

        [embedding] = embed_texts([item.question])
        top20 = retrieve_top_k(db, doc_id, embedding, k=TOP_K_RETRIEVE)
        if not top20:
            rows.append(
                RetrievalRow(
                    item_id=item.id, language=item.language,
                    hit_at_5=False, mrr=0.0, top5_pages=[], top5_scores=[],
                )
            )
            continue

        text_path = top20[0]["text_storage_path"]
        chunks_blob = storage.download(db, storage.BUCKET_CHUNKS, text_path)
        text_by_index = {
            c["chunk_index"]: c["text"]
            for c in json.loads(chunks_blob.decode("utf-8"))
        }
        for c in top20:
            c["text"] = text_by_index.get(c["chunk_index"], "")

        top5 = rerank(item.question, top20, k=TOP_K_RERANK)
        top5_texts = [c["text"] for c in top5]
        idx = _hit_index(top5_texts, item.expected_chunk_text_excerpt)

        rows.append(
            RetrievalRow(
                item_id=item.id,
                language=item.language,
                hit_at_5=idx is not None,
                mrr=(1.0 / (idx + 1)) if idx is not None else 0.0,
                top5_pages=[c["page_number"] for c in top5],
                top5_scores=[round(c.get("score", 0.0), 4) for c in top5],
            )
        )

    n = len(rows)
    if n == 0:
        return RetrievalReport(n=0, hit_at_5=0.0, mrr=0.0, by_language={}, rows=[])

    hit_at_5 = sum(1 for r in rows if r.hit_at_5) / n
    mrr = sum(r.mrr for r in rows) / n

    by_lang: dict[str, dict[str, float]] = {}
    for lang in {r.language for r in rows}:
        lang_rows = [r for r in rows if r.language == lang]
        by_lang[lang] = {
            "n": len(lang_rows),
            "hit_at_5": sum(1 for r in lang_rows if r.hit_at_5) / len(lang_rows),
            "mrr": sum(r.mrr for r in lang_rows) / len(lang_rows),
        }

    return RetrievalReport(
        n=n,
        hit_at_5=hit_at_5,
        mrr=mrr,
        by_language=by_lang,
        rows=rows,
    )
