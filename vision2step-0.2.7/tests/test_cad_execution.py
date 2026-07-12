"""Offline tests for immutable candidate management."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.test_source_policy import VALID_SOURCE
from vision2step.cad_execution import CadExecutionService
from vision2step.errors import CandidateExecutionError

FAKE_METRICS = {
    "valid": True,
    "shape_type": "Solid",
    "solid_count": 1,
    "dimensions_mm": {"x": 120.0, "y": 60.0, "z": 10.0},
    "volume_mm3": 72000.0,
    "area_mm2": 16800.0,
    "step_reopened": True,
    "step_reopened_valid": True,
    "step_reopened_solid_count": 1,
}


def fake_runner(arguments: list[str], cwd: Path) -> dict[str, Any]:
    del cwd
    if arguments[0] == "build":
        Path(arguments[2]).write_text("ISO-10303-21;", encoding="utf-8")
    return dict(FAKE_METRICS)


def failing_runner(arguments: list[str], cwd: Path) -> dict[str, Any]:
    del arguments, cwd
    raise CandidateExecutionError("simulated execution failure")


class CadExecutionServiceTests(unittest.TestCase):
    def test_build_creates_immutable_candidate_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = CadExecutionService(directory, runner=fake_runner)
            result = service.build_candidate("board_001", VALID_SOURCE)
            files = {item["name"] for item in service.list_candidate_artifacts("board_001")}
            validation = service.validate_step("board_001")

            self.assertEqual(result["status"], "valid")
            self.assertEqual(validation["solid_count"], 1)
            self.assertEqual(
                files,
                {"manifest.json", "metrics.json", "model.py", "model.step"},
            )
            with self.assertRaises(CandidateExecutionError):
                service.build_candidate("board_001", VALID_SOURCE)


    def test_failed_candidate_is_archived_and_id_can_be_retried(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            failing_service = CadExecutionService(directory, runner=failing_runner)
            with self.assertRaises(CandidateExecutionError):
                failing_service.build_candidate("board_001", VALID_SOURCE)

            successful_service = CadExecutionService(directory, runner=fake_runner)
            result = successful_service.build_candidate("board_001", VALID_SOURCE)
            archived = list((Path(directory) / "_failed").glob("board_001-*"))

            self.assertEqual(result["status"], "valid")
            self.assertEqual(len(archived), 1)
            self.assertTrue((archived[0] / "manifest.json").is_file())


    def test_timeout_error_reports_last_runner_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = CadExecutionService(directory, timeout_seconds=1)
            timeout = subprocess.TimeoutExpired(
                cmd=["python"],
                timeout=1,
                stderr="vision2step-stage:step_export\n",
            )
            with (
                patch("vision2step.cad_execution.subprocess.run", side_effect=timeout),
                self.assertRaisesRegex(CandidateExecutionError, "step_export"),
            ):
                service._run(["build", "model.py", "model.step"], Path(directory))


    def test_timeout_error_uses_stage_file_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            service = CadExecutionService(directory, timeout_seconds=1)

            def timeout_after_stage(*args: object, **kwargs: object) -> object:
                del args, kwargs
                (cwd / "last-stage.txt").write_text(
                    "source_statement_6_lines_18-33\n", encoding="utf-8"
                )
                raise subprocess.TimeoutExpired(cmd=["python"], timeout=1)

            with (
                patch(
                    "vision2step.cad_execution.subprocess.run",
                    side_effect=timeout_after_stage,
                ),
                self.assertRaisesRegex(
                    CandidateExecutionError,
                    r"source statement 6 .*model\.py lines 18-33",
                ),
            ):
                service._run(["build", "model.py", "model.step"], cwd)

    def test_timeout_before_first_runner_stage_reports_startup_problem(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = CadExecutionService(directory, timeout_seconds=1)
            timeout = subprocess.TimeoutExpired(cmd=["python"], timeout=1)
            with (
                patch("vision2step.cad_execution.subprocess.run", side_effect=timeout),
                self.assertRaisesRegex(
                    CandidateExecutionError,
                    "before the isolated runner reported its first stage",
                ),
            ):
                service._run(["build", "model.py", "model.step"], Path(directory))

    def test_candidate_id_cannot_traverse_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = CadExecutionService(directory, runner=fake_runner)

            with self.assertRaises(CandidateExecutionError):
                service.build_candidate("../escape", VALID_SOURCE)


if __name__ == "__main__":
    unittest.main()
