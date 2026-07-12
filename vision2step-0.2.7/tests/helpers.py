"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from vision2step.models import AnalysisArtifact, CADObjectSpecification


def example_artifact() -> AnalysisArtifact:
    path = Path(__file__).parents[1] / "examples" / "illustrative_analysis.json"
    return AnalysisArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


def example_specification() -> CADObjectSpecification:
    return example_artifact().specification

