"""Candidate workspace management and restricted CadQuery subprocess execution."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from vision2step.errors import CandidateExecutionError
from vision2step.runtime_environment import sanitized_runtime_environment
from vision2step.source_policy import validate_cadquery_source

CANDIDATE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
Runner = Callable[[list[str], Path], dict[str, Any]]


class CadExecutionService:
    """Create immutable candidate folders and invoke the isolated CAD runner."""

    def __init__(
        self,
        candidate_root: str | Path,
        *,
        timeout_seconds: int = 120,
        runner: Runner | None = None,
    ) -> None:
        self.candidate_root = Path(candidate_root).expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self._runner = runner

    @classmethod
    def from_environment(cls) -> CadExecutionService:
        return cls(
            os.getenv("VISION2STEP_CANDIDATE_ROOT", "artifacts/candidates"),
            timeout_seconds=int(os.getenv("VISION2STEP_CAD_TIMEOUT", "120")),
        )

    def build_candidate(self, candidate_id: str, cadquery_source: str) -> dict[str, Any]:
        candidate_dir = self._candidate_dir(candidate_id)
        if candidate_dir.exists():
            self._archive_failed_candidate(candidate_id, candidate_dir)

        policy = validate_cadquery_source(cadquery_source)
        candidate_dir.mkdir(parents=True)
        script_path = candidate_dir / "model.py"
        step_path = candidate_dir / "model.step"
        metrics_path = candidate_dir / "metrics.json"
        manifest_path = candidate_dir / "manifest.json"
        script_path.write_text(cadquery_source.rstrip() + "\n", encoding="utf-8")

        try:
            metrics = self._run(["build", str(script_path), str(step_path)], candidate_dir)
            metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            manifest = {
                "candidate_id": candidate_id,
                "status": "valid",
                "created_at": datetime.now(UTC).isoformat(),
                "source_policy": policy.as_dict(),
                "artifacts": ["model.py", "model.step", "metrics.json", "manifest.json"],
            }
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            return {"status": "valid", "candidate_id": candidate_id, "metrics": metrics}
        except Exception as exc:
            manifest = {
                "candidate_id": candidate_id,
                "status": "failed",
                "created_at": datetime.now(UTC).isoformat(),
                "source_policy": policy.as_dict(),
                "error": str(exc),
                "artifacts": [
                    name
                    for name in ("model.py", "manifest.json", "last-stage.txt")
                    if name != "last-stage.txt" or (candidate_dir / name).is_file()
                ],
            }
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            if isinstance(exc, CandidateExecutionError):
                raise
            raise CandidateExecutionError(str(exc)) from exc

    def validate_step(self, candidate_id: str) -> dict[str, Any]:
        candidate_dir = self._candidate_dir(candidate_id)
        step_path = candidate_dir / "model.step"
        if not step_path.is_file():
            raise CandidateExecutionError(f"STEP file does not exist for {candidate_id}.")
        return self._run(["inspect", str(step_path)], candidate_dir)

    def inspect_model(self, candidate_id: str) -> dict[str, Any]:
        metrics_path = self._candidate_dir(candidate_id) / "metrics.json"
        if not metrics_path.is_file():
            raise CandidateExecutionError(f"Metrics do not exist for {candidate_id}.")
        return cast(
            dict[str, Any],
            json.loads(metrics_path.read_text(encoding="utf-8")),
        )

    def list_candidate_artifacts(self, candidate_id: str) -> list[dict[str, Any]]:
        candidate_dir = self._candidate_dir(candidate_id)
        if not candidate_dir.is_dir():
            raise CandidateExecutionError(f"Candidate does not exist: {candidate_id}")
        return [
            {"name": path.name, "size_bytes": path.stat().st_size}
            for path in sorted(candidate_dir.iterdir())
            if path.is_file()
        ]

    def _archive_failed_candidate(self, candidate_id: str, candidate_dir: Path) -> None:
        manifest_path = candidate_dir / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            raise CandidateExecutionError(
                f"Candidate already exists and will not be overwritten: {candidate_id}"
            ) from exc

        if manifest.get("status") != "failed":
            raise CandidateExecutionError(
                f"Candidate already exists and will not be overwritten: {candidate_id}"
            )

        failed_root = self.candidate_root / "_failed"
        failed_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        archived_dir = failed_root / f"{candidate_id}-{timestamp}"
        candidate_dir.rename(archived_dir)

    def _candidate_dir(self, candidate_id: str) -> Path:
        if not CANDIDATE_ID_PATTERN.fullmatch(candidate_id):
            raise CandidateExecutionError(
                "Candidate ID must use 1-64 letters, numbers, underscores, or hyphens."
            )
        return self.candidate_root / candidate_id

    def _run(self, arguments: list[str], cwd: Path) -> dict[str, Any]:
        if self._runner is not None:
            return self._runner(arguments, cwd)

        environment = sanitized_runtime_environment()
        command = [sys.executable, "-I", "-m", "vision2step.cad_runner", *arguments]
        stage_file = cwd / "last-stage.txt"
        with suppress(OSError):
            stage_file.write_text("runner_process_starting\n", encoding="utf-8")
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stderr = exc.stderr or ""
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            stages = re.findall(r"vision2step-stage:([^\r\n]+)", stderr)
            stage = stages[-1] if stages else ""
            if not stage:
                try:
                    stage = stage_file.read_text(encoding="utf-8").strip()
                except OSError:
                    stage = ""

            statement_match = re.fullmatch(r"source_statement_(\d+)_lines_(\d+)-(\d+)", stage)
            if stage == "runner_process_starting":
                stage_detail = " before the isolated runner reported its first stage"
                guidance = (
                    "The runner did not start correctly. This usually indicates a subprocess "
                    "environment or interpreter startup problem."
                )
            elif statement_match:
                number, first_line, last_line = statement_match.groups()
                stage_detail = (
                    f" while executing source statement {number} "
                    f"(model.py lines {first_line}-{last_line})"
                )
                guidance = (
                    "This usually indicates pathological generated geometry; increasing the "
                    "timeout again is unlikely to help. Inspect the retained model.py statement "
                    "instead."
                )
            elif stage:
                stage_detail = f" during stage `{stage}`"
                guidance = (
                    "The recorded stage identifies where execution stopped; increasing the "
                    "timeout again may not help."
                )
            else:
                stage_detail = ""
                guidance = "The runner produced no startup diagnostic."

            raise CandidateExecutionError(
                f"CadQuery execution exceeded {self.timeout_seconds} seconds{stage_detail}. "
                f"{guidance}"
            ) from exc

        stdout = completed.stdout[-20_000:]
        stderr = completed.stderr[-20_000:]
        if completed.returncode != 0:
            detail = stderr.strip() or stdout.strip() or "Unknown subprocess failure."
            raise CandidateExecutionError(detail)
        try:
            return cast(dict[str, Any], json.loads(stdout.strip()))
        except json.JSONDecodeError as exc:
            raise CandidateExecutionError("CAD runner returned invalid JSON output.") from exc
