"""
Language detection using langdetect (MIT).

Deterministic via the seed below — same text always returns the same code.
Returns None for empty / too-short / undetectable text rather than raising,
so callers don't need to defensively guard every site.
"""

from __future__ import annotations

import logging

from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0  # determinism

logger = logging.getLogger(__name__)

_MIN_SAMPLE_CHARS = 20
_MAX_SAMPLE_CHARS = 4096


def detect_language(text: str) -> str | None:
    """
    Return ISO 639-1 language code (e.g. 'en', 'hi', 'ta') or None.
    """
    sample = text.strip()
    if len(sample) < _MIN_SAMPLE_CHARS:
        return None
    try:
        return detect(sample[:_MAX_SAMPLE_CHARS])
    except LangDetectException:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("lang detection failed: %s", exc)
        return None
