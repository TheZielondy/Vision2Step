"""Tests for the local, token-free silhouette measurement pass."""

from __future__ import annotations

import unittest
from io import BytesIO

from PIL import Image, ImageDraw

from vision2step.geometry_hints import extract_geometry_hints


class GeometryHintsTests(unittest.TestCase):
    def test_horizontal_profile_and_oval_hole_are_measured(self) -> None:
        image = Image.new("RGB", (420, 240), "white")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((20, 45, 300, 195), radius=15, fill=(145, 90, 35))
        draw.rectangle((280, 90, 365, 150), fill=(145, 90, 35))
        draw.ellipse((335, 75, 405, 165), fill=(145, 90, 35))
        draw.ellipse((360, 100, 382, 140), fill="white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")

        hints = extract_geometry_hints(buffer.getvalue())

        self.assertIsNotNone(hints)
        assert hints is not None
        self.assertEqual(hints.dominant_axis, "horizontal")
        self.assertGreater(hints.object_aspect_ratio, 2.0)
        self.assertEqual(hints.confidence, "high")
        self.assertEqual(len(hints.enclosed_regions), 1)
        self.assertGreater(hints.enclosed_regions[0].height, hints.enclosed_regions[0].width)


if __name__ == "__main__":
    unittest.main()
