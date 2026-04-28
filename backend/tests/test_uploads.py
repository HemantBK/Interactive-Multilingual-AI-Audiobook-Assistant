"""Unit tests for app.services.uploads — pure-function validation."""

from __future__ import annotations

import pytest

from app.services import uploads as u
from app.services.uploads import (
    UploadValidationError,
    assert_size,
    detect_source_type,
)


# ---------- size ----------

def test_assert_size_accepts_small() -> None:
    assert_size(b"hello")


def test_assert_size_rejects_empty() -> None:
    with pytest.raises(UploadValidationError) as exc:
        assert_size(b"")
    assert exc.value.status_code == 400


def test_assert_size_rejects_oversized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(u, "MAX_UPLOAD_BYTES", 5)
    with pytest.raises(UploadValidationError) as exc:
        assert_size(b"hello world")
    assert exc.value.status_code == 413


# ---------- MIME + magic bytes ----------

def test_detect_pdf_accepts_real_magic() -> None:
    source, mime, ext = detect_source_type(b"%PDF-1.4\nfoo", "application/pdf")
    assert (source, mime, ext) == ("pdf", "application/pdf", "pdf")


def test_detect_pdf_rejects_wrong_magic() -> None:
    with pytest.raises(UploadValidationError) as exc:
        detect_source_type(b"GIF89a...", "application/pdf")
    assert exc.value.status_code == 400


def test_detect_jpeg_accepts_real_magic() -> None:
    source, mime, ext = detect_source_type(b"\xff\xd8\xff\xe0...", "image/jpeg")
    assert (source, ext) == ("image", "jpg")


def test_detect_png_accepts_real_magic() -> None:
    source, _, ext = detect_source_type(b"\x89PNG\r\n\x1a\nrest...", "image/png")
    assert (source, ext) == ("image", "png")


def test_detect_webp_accepts_real_magic() -> None:
    blob = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"VP8 ..."
    source, _, ext = detect_source_type(blob, "image/webp")
    assert (source, ext) == ("image", "webp")


def test_detect_webp_rejects_riff_without_webp() -> None:
    blob = b"RIFF" + b"\x00\x00\x00\x00" + b"AVI " + b"..."
    with pytest.raises(UploadValidationError):
        detect_source_type(blob, "image/webp")


def test_detect_unsupported_mime() -> None:
    with pytest.raises(UploadValidationError) as exc:
        detect_source_type(b"x", "application/x-shockwave-flash")
    assert exc.value.status_code == 415


def test_detect_text_utf8_accepts_indic() -> None:
    source, _, _ = detect_source_type("नमस्ते दुनिया".encode("utf-8"), "text/plain")
    assert source == "text"


def test_detect_text_rejects_non_utf8() -> None:
    with pytest.raises(UploadValidationError):
        detect_source_type(b"\xff\xfe\x00\x00invalid", "text/plain")


def test_detect_missing_mime_rejected() -> None:
    with pytest.raises(UploadValidationError) as exc:
        detect_source_type(b"%PDF-", None)
    assert exc.value.status_code == 415
