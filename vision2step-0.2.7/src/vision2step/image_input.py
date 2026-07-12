"""Local image validation and Claude-compatible encoding."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vision2step.errors import InvalidImageError
from vision2step.models import SourceImage

MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _detect_media_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@dataclass(frozen=True)
class EncodedImage:
    """An image payload plus non-sensitive provenance metadata."""

    path: Path
    media_type: str
    data: bytes

    @classmethod
    def from_path(cls, image_path: str | Path) -> EncodedImage:
        path = Path(image_path).expanduser().resolve()
        if not path.is_file():
            raise InvalidImageError(f"Image does not exist or is not a file: {path}")

        data = path.read_bytes()
        if not data:
            raise InvalidImageError(f"Image is empty: {path.name}")
        if len(data) > MAX_IMAGE_BYTES:
            raise InvalidImageError(
                f"Image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit: {path.name}"
            )

        media_type = _detect_media_type(data)
        if media_type is None:
            raise InvalidImageError(
                f"Unsupported image format for {path.name}; use JPEG, PNG, GIF, or WebP."
            )
        return cls(path=path, media_type=media_type, data=data)

    def as_content_block(self) -> dict[str, Any]:
        """Return a base64 image block accepted by the Claude Messages API."""

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": self.media_type,
                "data": base64.b64encode(self.data).decode("ascii"),
            },
        }

    def source_metadata(self) -> SourceImage:
        """Return reproducibility metadata without exposing an absolute local path."""

        return SourceImage(
            file_name=self.path.name,
            media_type=self.media_type,
            byte_size=len(self.data),
            sha256=hashlib.sha256(self.data).hexdigest(),
        )

