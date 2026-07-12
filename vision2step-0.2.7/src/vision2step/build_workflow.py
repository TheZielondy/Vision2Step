"""Deterministic controller joining Builder Claude to isolated CAD execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vision2step.cad_execution import CadExecutionService
from vision2step.errors import CandidateExecutionError
from vision2step.models import BuilderArtifact


def execute_cadquery_source(
    cadquery_source: str,
    *,
    candidate_id: str,
    candidate_root: str | Path,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Build retained source through the isolated executor without calling Claude."""

    root = Path(candidate_root).expanduser().resolve()
    service = CadExecutionService(root, timeout_seconds=timeout_seconds)
    return service.build_candidate(candidate_id, cadquery_source)


def execute_builder_artifact(
    artifact: BuilderArtifact,
    *,
    candidate_id: str,
    candidate_root: str | Path,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Persist a proposal, build it in isolation, and retain candidate provenance."""

    root = Path(candidate_root).expanduser().resolve()
    proposal_dir = root / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = proposal_dir / f"{candidate_id}.json"
    if proposal_path.exists():
        raise CandidateExecutionError(f"Proposal already exists: {candidate_id}")
    proposal_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

    try:
        result = execute_cadquery_source(
            artifact.proposal.cadquery_source,
            candidate_id=candidate_id,
            candidate_root=root,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        # A full build proposal is staging data. Do not consume an immutable candidate ID
        # when validation or CAD execution fails before a candidate is created.
        proposal_path.unlink(missing_ok=True)
        raise

    candidate_dir = root / candidate_id
    candidate_proposal = candidate_dir / "builder-proposal.json"
    candidate_proposal.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "builder-proposal.json" not in manifest["artifacts"]:
        manifest["artifacts"].append("builder-proposal.json")
    manifest["source_analysis_id"] = artifact.source_analysis_id
    manifest["builder_model"] = artifact.model
    manifest["builder_token_usage"] = artifact.token_usage.model_dump()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return result
