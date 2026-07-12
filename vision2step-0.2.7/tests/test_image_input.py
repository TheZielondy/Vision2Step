"""Tests for local image validation and encoding."""

from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from vision2step.errors import InvalidImageError
from vision2step.image_input import EncodedImage

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class EncodedImageTests(unittest.TestCase):
    def test_png_is_encoded_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "reference.png"
            image_path.write_bytes(TINY_PNG)

            encoded = EncodedImage.from_path(image_path)
            block = encoded.as_content_block()
            metadata = encoded.source_metadata()

        self.assertEqual(encoded.media_type, "image/png")
        self.assertEqual(base64.b64decode(block["source"]["data"]), TINY_PNG)
        self.assertEqual(metadata.file_name, "reference.png")
        self.assertEqual(len(metadata.sha256), 64)
        self.assertNotIn(directory, metadata.file_name)

    def test_unknown_file_signature_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fake.png"
            path.write_text("not an image", encoding="utf-8")

            with self.assertRaises(InvalidImageError):
                EncodedImage.from_path(path)


if __name__ == "__main__":
    unittest.main()

