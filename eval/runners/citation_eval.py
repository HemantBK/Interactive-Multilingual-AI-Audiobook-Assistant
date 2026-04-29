"""
Citation precision via LLM-as-judge (build plan §8 Day 23).

For each citation-set golden item:
  1. Run the production RAG pipeline against the labelled doc + question.
  2. For every emitted citation, ask Groq Llama 3.3 70B (forced JSON mode):
       "Does <quote> appear in <chunk text>, AND is the answer's claim
        supported by that quote?"
  3. Citation precision = supported / total.

Why LLM-as-judge: hand-grading 100 Q/A pairs per release is the only
alternative; our deterministic citation validator (Day 9) only checks
substring presence, not semantic support. See build plan §8.

Lightweight: no ragas dep, no extra HF model. Single Groq call per
citation, cached at the prompt level by Groq's deduplication.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

from app.db.supabase import admin_client
from app.services.groq_client import DEFAULT_MODEL, groq_stream_chat
from app.services.rag import stream_rag_answer

from .loader import GoldenItem

logger = logging.getLogger(__name__)

JUDGE_SYSTEM = """\
You are an evaluation judge. Given an ANSWER, a CITED QUOTE, and the
SOURCE CHUNK that the quote was supposedly drawn from, decide whether
the quote (a) appears verbatim or near-verbatim in the chunk, AND
(b) substantively supports the answer's claim.

Output ONLY a single JSON object:
  {"supported": true|false, "reason": "<one short sentence>"}
"""


@dataclass
class CitationRow:
    item_id: str
    n_citations: int
    n_supported: int
    precision: float
    sample_reasons: list[str]


@dataclass
class CitationReport:
    n: int
    precision: float
    rows: list[CitationRow]

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "precision": self.precision,
            "rows": [r.__dict__ for r in self.rows],
        }


async def _judge_one(
    answer: str, quote: str, chunk_text: str
) -> tuple[bool, str]:
    user = (
        f"<answer>{answer}</answer>\n"
        f"<cited_quote>{quote}</cited_quote>\n"
        f"<source_chunk>{chunk_text}</source_chunk>"
    )
    parts: list[str] = []
    async for tok in groq_stream_chat(
        [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user},
        ],
        model=DEFAULT_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
    ):
        parts.append(tok)
    try:
        parsed = json.loads("".join(parts).strip())
        return bool(parsed.get("supported", False)), str(parsed.get("reason", ""))
    except json.JSONDecodeError:
        return False, "judge returned non-JSON"


async def evaluate_citations(
    items: list[GoldenItem],
    doc_id_by_path: dict[str, str],
    *,
    user_id: str,
) -> CitationReport:
    """user_id needed only because conversations write happens during RAG.
    Pass any service-account UUID; eval runs aren't surfaced to humans."""
    db = admin_client()
    rows: list[CitationRow] = []

    for item in items:
        doc_id = doc_id_by_path.get(item.doc_path)
        if not doc_id:
            logger.warning("skip %s: no doc id for %s", item.id, item.doc_path)
            continue

        # Drive the live RAG pipeline. Capture the answer + citations + chunks.
        answer = ""
        citations: list[dict] = []
        retrieved_chunks: list[dict] = []
        async for ev in stream_rag_answer(db, user_id, doc_id, item.question):
            if ev["event"] == "answer":
                answer = ev["answer"]
                citations = ev["citations"]
            elif ev["event"] == "done":
                retrieved_chunks = ev["retrieved_chunks"]

        chunk_text_by_id = {
            c["id"]: text_excerpt(c.get("bbox"), retrieved_chunks)
            for c in retrieved_chunks
        }
        # The text isn't carried in retrieved_chunks; pull from chunks bucket
        # via the existing rag pipeline behaviour. For Day 23, we're checking
        # quote-vs-chunk; chunk_text comes from re-resolving via the RPC.
        # Simpler shortcut: use the citation's chunk_id to look up a chunk's
        # text via document_chunks table directly (already RLS-authorised
        # under admin_client).
        chunk_id_to_text: dict[int, str] = {}
        if citations:
            ids = [c["chunk_id"] for c in citations]
            res = (
                db.table("document_chunks")
                .select("id, text_storage_path, chunk_index")
                .in_("id", ids)
                .execute()
            )
            # Fetch each unique storage path once.
            from app.services import storage

            paths_seen: dict[str, dict[int, str]] = {}
            for row in res.data or []:
                p = row["text_storage_path"]
                if p not in paths_seen:
                    blob = storage.download(db, storage.BUCKET_CHUNKS, p)
                    paths_seen[p] = {
                        c["chunk_index"]: c["text"]
                        for c in json.loads(blob.decode("utf-8"))
                    }
                chunk_id_to_text[row["id"]] = paths_seen[p].get(row["chunk_index"], "")

        n_supported = 0
        reasons: list[str] = []
        for cit in citations:
            chunk_text = chunk_id_to_text.get(cit["chunk_id"], "")
            if not chunk_text:
                reasons.append("chunk text unavailable")
                continue
            supported, reason = await _judge_one(answer, cit["quote"], chunk_text)
            if supported:
                n_supported += 1
            else:
                reasons.append(reason)

        rows.append(
            CitationRow(
                item_id=item.id,
                n_citations=len(citations),
                n_supported=n_supported,
                precision=(n_supported / len(citations)) if citations else 0.0,
                sample_reasons=reasons[:3],
            )
        )

    total_cit = sum(r.n_citations for r in rows)
    total_sup = sum(r.n_supported for r in rows)
    precision = (total_sup / total_cit) if total_cit else 0.0
    return CitationReport(n=len(rows), precision=precision, rows=rows)


def text_excerpt(_bbox, _retrieved):  # noqa: D401 — present for symmetry, unused
    return ""
