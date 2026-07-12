"""Tests for proposal staging in the Step 2 build workflow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vision2step.build_workflow import execute_builder_artifact
from vision2step.errors import CandidateExecutionError


class FailingCadExecutionService:
    def __init__(self, candidate_root: Path, *, timeout_seconds: int = 30) -> None:
        del candidate_root, timeout_seconds

    def build_candidate(self, candidate_id: str, cadquery_source: str) -> dict[str, object]:
        del candidate_id, cadquery_source
        raise CandidateExecutionError("policy failure")


class BuildWorkflowTests(unittest.TestCase):
    def test_failed_build_removes_staged_proposal(self) -> None:
        artifact = SimpleNamespace(
            proposal=SimpleNamespace(
                cadquery_source='import cadquery as cq\nresult = cq.Workplane("XY").box(1, 1, 1)\n'
            ),
            source_analysis_id="analysis-test",
            model="builder-test",
            token_usage=SimpleNamespace(model_dump=lambda: {}),
            model_dump_json=lambda indent=2: '{"proposal":"test"}',
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proposal_path = root / "proposals" / "board_001.json"
            with (
                patch(
                    "vision2step.build_workflow.CadExecutionService",
                    FailingCadExecutionService,
                ),
                self.assertRaises(CandidateExecutionError),
            ):
                execute_builder_artifact(
                    artifact,
                    candidate_id="board_001",
                    candidate_root=root,
                )

            self.assertFalse(proposal_path.exists())


if __name__ == "__main__":
    unittest.main()
