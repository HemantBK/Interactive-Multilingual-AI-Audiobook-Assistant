"""
bge-reranker-v2-m3 cross-encoder (sentence-transformers, MIT).

A cross-encoder runs the (question, chunk) pair through one transformer
forward pass, producing a relevance score. Slower than dual-encoder retrieval
but materially more accurate at the top — critical for the 90% citation
precision target (build plan A2 §8).

CPU latency on HF Spaces 2-vCPU: ~150 ms for 20 candidates. Bounded by the
top-k from retrieval, not by document size.

Lazy singleton load to keep cold start fast (build plan A2 §3).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Final

logger = logging.getLogger(__name__)

RERANKER_NAME: Final = "BAAI/bge-reranker-v2-m3"
RERANKER_VERSION: Final = "bge-reranker-v2-m3@1.0"

_model = None
_lock = threading.Lock()


def _load_model():
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        logger.info("loading reranker: %s", RERANKER_NAME)
        from sentence_transformers import CrossEncoder

        _model = CrossEncoder(RERANKER_NAME, device="cpu", max_length=512)
        logger.info("loaded reranker %s", RERANKER_NAME)
    return _model


def rerank(
    question: str,
    candidates: list[dict[str, Any]],
    *,
    k: int = 5,
) -> list[dict[str, Any]]:
    """
    Score (question, candidate.text) pairs and return top-k by score desc.
    Each input candidate must carry a 'text' field. The returned dicts gain
    a 'score' field (float). Originals are not mutated.
    """
    if not candidates:
        return []

    model = _load_model()
    pairs = [(question, c.get("text", "")) for c in candidates]
    scores = model.predict(pairs, show_progress_bar=False)

    scored: list[dict[str, Any]] = []
    for c, s in zip(candidates, scores, strict=True):
        scored.append({**c, "score": float(s)})
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:k]
