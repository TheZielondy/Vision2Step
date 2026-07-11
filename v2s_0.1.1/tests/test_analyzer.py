"""Offline tests for the Claude analyzer orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image, ImageDraw

from vision2step.analyzer import AnalyzerConfig, VisionAnalyzer
from vision2step.errors import AnalyzerResponseError
from vision2step.models import CADObjectSpecification, Unit
from tests.helpers import example_specification

class FakeMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return self.response


class FakeClient:
    def __init__(self, response: Any) -> None:
        self.messages = FakeMessages(response)


class VisionAnalyzerTests(unittest.TestCase):
    def _image_path(self, directory: str) -> Path:
        path = Path(directory) / "part.png"
        image = Image.new("RGB", (200, 120), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 30, 180, 90), fill="black")
        draw.ellipse((145, 45, 165, 75), fill="white")
        image.save(path)
        return path

    def test_analyzer_builds_image_first_request_and_wraps_provenance(self) -> None:
        response = SimpleNamespace(
            id="msg_test",
            stop_reason="end_turn",
            parsed_output=example_specification(),
            usage=SimpleNamespace(input_tokens=120, output_tokens=340),
        )
        client = FakeClient(response)
        config = AnalyzerConfig(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            preferred_unit=Unit.MILLIMETER,
        )

        with tempfile.TemporaryDirectory() as directory:
            artifact = VisionAnalyzer(client=client, config=config).analyze(
                [self._image_path(directory)],
                object_context="Overall height is 80 mm.",
            )

        request = client.messages.kwargs
        content = request["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "image")
        self.assertEqual(content[-1]["type"], "text")
        self.assertTrue(
            any("deterministic measurements" in block.get("text", "") for block in content)
        )
        self.assertIn("Overall height is 80 mm.", content[-1]["text"])
        self.assertIs(request["output_format"], CADObjectSpecification)
        self.assertEqual(artifact.response_id, "msg_test")
        self.assertEqual(artifact.token_usage.input_tokens, 120)
        self.assertEqual(artifact.source_images[0].file_name, "part.png")

    def test_truncated_structured_output_is_rejected(self) -> None:
        response = SimpleNamespace(
            id="msg_test",
            stop_reason="max_tokens",
            parsed_output=None,
            usage=SimpleNamespace(input_tokens=120, output_tokens=1000),
        )
        client = FakeClient(response)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AnalyzerResponseError):
                VisionAnalyzer(client=client).analyze([self._image_path(directory)])


if __name__ == "__main__":
    unittest.main()
