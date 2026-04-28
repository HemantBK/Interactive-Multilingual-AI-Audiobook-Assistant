"""
Upload validation + EXIF strip.

Order matters:
  1. size check (bail early on 50 MB+ blobs)
  2. magic-byte sniff (defense-in-depth — never trust client MIME)
  3. format-specific cleaning (EXIF strip on images)

Everything stays in memory (BytesIO). HF Spaces has small disk quotas.
"""

from __future__ import annotations

from io import BytesIO
from typing import Literal

from PIL import Image

from app.core.config import settings

SourceType = Literal["pdf", "image", "text"]

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024

_PDF = "application/pdf"
_JPEG = "image/jpeg"
_PNG = "image/png"
_WEBP = "image/webp"
_TEXT = "text/plain"

# (magic_bytes_prefix, source_type, output_extension)
_ACCEPTED: dict[str, tuple[bytes, SourceType, str]] = {
    _PDF: (b"%PDF-", "pdf", "pdf"),
    _JPEG: (b"\xff\xd8\xff", "image", "jpg"),
    _PNG: (b"\x89PNG\r\n\x1a\n", "image", "png"),
    _WEBP: (b"", "image", "webp"),  # checked by RIFF/WEBP at offset 0/8
    _TEXT: (b"", "text", "txt"),    # checked via UTF-8 decode
}


class UploadValidationError(Exception):
    """Validation rejection. status_code drives the HTTP response."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def assert_size(content: bytes) -> None:
    if len(content) == 0:
        raise UploadValidationError(400, "Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadValidationError(
            413, f"File exceeds {settings.max_upload_mb} MB cap"
        )


def detect_source_type(
    content: bytes, declared_mime: str | None
) -> tuple[SourceType, str, str]:
    """
    Validate declared MIME against magic bytes.
    Returns (source_type, real_mime, output_extension). Raises on mismatch.
    """
    if declared_mime not in _ACCEPTED:
        raise UploadValidationError(415, f"Unsupported MIME: {declared_mime!r}")

    expected_magic, source_type, ext = _ACCEPTED[declared_mime]

    if declared_mime == _WEBP:
        if (
            len(content) < 12
            or content[0:4] != b"RIFF"
            or content[8:12] != b"WEBP"
        ):
            raise UploadValidationError(400, "WEBP magic bytes mismatch")
    elif declared_mime == _TEXT:
        try:
            content[:8192].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UploadValidationError(
                400, "text/plain content is not valid UTF-8"
            ) from exc
    else:
        if not content.startswith(expected_magic):
            raise UploadValidationError(
                400, f"Magic bytes mismatch for declared MIME {declared_mime}"
            )

    return source_type, declared_mime, ext


def strip_exif(content: bytes, mime: str) -> bytes:
    """
    Re-encode an image without metadata. Pillow's `save` excludes EXIF unless
    explicitly passed it, so a load+save round-trip drops EXIF/GPS/etc cleanly.
    """
    if mime not in (_JPEG, _PNG, _WEBP):
        return content

    try:
        img = Image.open(BytesIO(content))
        img.load()
    except Exception as exc:
        raise UploadValidationError(400, f"Cannot decode image: {exc}") from exc

    out = BytesIO()
    save_kwargs: dict = {}
    if mime == _JPEG:
        save_kwargs.update(quality=92, optimize=True)
    img.save(out, format=img.format, **save_kwargs)
    return out.getvalue()
