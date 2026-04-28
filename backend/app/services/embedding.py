"""
bge-m3 embedding service (sentence-transformers, Apache-2.0).

Cold start: first encode() loads the model (~568 MB, ~30 s on free HF
Spaces). Once loaded, the model stays resident for the worker's lifetime.
We do NOT pre-load on FastAPI startup because /health needs to respond
before the model is ready (HF Spaces' wakeup race).

Output: 1024-dim float vectors, L2-normalised. Cast to halfvec(1024) at
insert time by Postgres. The MODEL_VERSION constant is stamped into every
chunk row so a future re-embedding job can target only stale rows.
"""

from __future__ import annotations

import logging
import threading
from typing import Final

logger = logging.getLogger(__name__)

MODEL_NAME: Final = "BAAI/bge-m3"
MODEL_VERSION: Final = "bge-m3@1.0"
EMBEDDING_DIM: Final = 1024

_model = None
_model_lock = threading.Lock()


def _load_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        logger.info("loading embedding model: %s", MODEL_NAME)
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME, device="cpu")
        logger.info(
            "loaded %s (dim=%d)",
            MODEL_NAME,
            _model.get_sentence_embedding_dimension(),
        )
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """One 1024-dim list per input text. Empty input → empty output."""
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors.tolist()
