"""Tests for token-free artifact enrichment."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tests.helpers import example_artifact
from vision2step.artifact_tools import enrich_analysis_geometry
from vision2step.errors import Vision2StepError
from vision2step.image_input import EncodedImage
from vision2step.models import AnalysisArtifact


class ArtifactEnrichmentTests(unittest.TestCase):
    def test_existing_analysis_is_enriched_without_changing_specification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "reference.png"
            image = Image.new("RGB", (200, 120), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((20, 30, 180, 90), fill="black")
            draw.ellipse((145, 45, 165, 75), fill="white")
            image.save(image_path)
            original = example_artifact()
            data = original.model_dump()
            data["source_images"] = [
                EncodedImage.from_path(image_path).source_metadata().model_dump()
            ]
            matching = AnalysisArtifact.model_validate(data)

            enriched = enrich_analysis_geometry(matching, [image_path])

        self.assertEqual(enriched.artifact_version, "1.3")
        self.assertEqual(enriched.specification, matching.specification)
        self.assertEqual(len(enriched.geometry_hints), 1)
        self.assertEqual(len(enriched.geometry_hints[0].enclosed_regions), 1)

    def test_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "wrong.png"
            Image.new("RGB", (20, 20), "black").save(image_path)

            with self.assertRaises(Vision2StepError):
                enrich_analysis_geometry(example_artifact(), [image_path])


if __name__ == "__main__":
    unittest.main()
