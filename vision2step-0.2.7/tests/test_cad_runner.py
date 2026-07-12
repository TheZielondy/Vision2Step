"""Tests for statement-level CadQuery source execution diagnostics."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from vision2step.cad_runner import (
    _execute_source_statement_by_statement,
    _require_single_valid_solid,
)


class CadRunnerTests(unittest.TestCase):
    def test_source_statements_execute_in_order_and_record_last_line_range(self) -> None:
        source = "A = 2\nB = (\n    A + 3\n)\n"
        namespace: dict[str, object] = {"__builtins__": {}}
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path.cwd()
            try:
                os.chdir(directory)
                _execute_source_statement_by_statement(
                    source, Path(directory) / "model.py", namespace
                )
                stage = Path("last-stage.txt").read_text(encoding="utf-8").strip()
            finally:
                os.chdir(cwd)

        self.assertEqual(namespace["B"], 5)
        self.assertEqual(stage, "source_statement_2_lines_2-4")

    def test_multiple_solids_are_rejected(self) -> None:
        metrics = {"valid": True, "solid_count": 2, "volume_mm3": 100.0}

        with self.assertRaisesRegex(ValueError, "exactly one valid solid"):
            _require_single_valid_solid(metrics, source="Candidate")


if __name__ == "__main__":
    unittest.main()
