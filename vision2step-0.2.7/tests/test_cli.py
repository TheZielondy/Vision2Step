"""Tests for token-free command-line paths."""

from __future__ import annotations

import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_source_policy import VALID_SOURCE
from vision2step.cli import _build_parser, _run_execute_source


class ExecuteSourceCliTests(unittest.TestCase):
    def test_execute_source_parser_requires_candidate_id(self) -> None:
        args = _build_parser().parse_args(
            ["execute-source", "model.py", "--candidate-id", "board_retry"]
        )

        self.assertEqual(args.command, "execute-source")
        self.assertEqual(args.candidate_id, "board_retry")
        self.assertEqual(args.source, Path("model.py"))

    def test_execute_source_builds_without_builder_claude(self) -> None:
        metrics = {"dimensions_mm": {"x": 1.0, "y": 2.0, "z": 3.0}}

        def execute_source(*args: object, **kwargs: object) -> dict[str, object]:
            del args, kwargs
            return {
                "status": "valid",
                "candidate_id": "board_retry",
                "metrics": metrics,
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "model.py"
            source_path.write_text(VALID_SOURCE, encoding="utf-8")
            args = argparse.Namespace(
                source=source_path,
                candidate_id="board_retry",
                candidate_root=root / "candidates",
                timeout=30,
            )
            output = io.StringIO()
            with (
                patch("vision2step.cli.execute_cadquery_source", side_effect=execute_source),
                contextlib.redirect_stdout(output),
            ):
                status = _run_execute_source(args)

        self.assertEqual(status, 0)
        self.assertIn("Claude API calls: 0", output.getvalue())


if __name__ == "__main__":
    unittest.main()
