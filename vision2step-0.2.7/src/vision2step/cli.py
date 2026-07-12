"""Command-line interface for the implemented Vision2STEP stages."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from vision2step.analyzer import AnalyzerConfig, VisionAnalyzer
from vision2step.artifact_tools import enrich_analysis_geometry
from vision2step.build_workflow import execute_builder_artifact, execute_cadquery_source
from vision2step.builder import BuilderConfig, CadBuilder
from vision2step.errors import Vision2StepError
from vision2step.models import AnalysisArtifact, Unit


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vision2step",
        description="Convert reference images into validated STEP candidates.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze one or more reference images.")
    analyze.add_argument("images", nargs="+", type=Path, help="JPEG, PNG, GIF, or WebP files.")
    analyze.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON path. Defaults to artifacts/<first-image>-analysis.json.",
    )
    analyze.add_argument(
        "--context",
        default="",
        help="Known object type, real dimension, or other evidence Claude should use.",
    )
    analyze.add_argument(
        "--unit",
        choices=[unit.value for unit in Unit],
        default=Unit.MILLIMETER.value,
        help="Preferred unit for estimates (default: mm).",
    )
    analyze.add_argument(
        "--model",
        default=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        help="Claude model ID.",
    )
    analyze.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("VISION2STEP_MAX_TOKENS", "3500")),
        help="Maximum structured-output tokens (default: 3500).",
    )

    enrich = subparsers.add_parser(
        "enrich",
        help="Add deterministic geometry hints to an existing analysis without Claude.",
    )
    enrich.add_argument("analysis", type=Path, help="Existing analyzer JSON artifact.")
    enrich.add_argument(
        "images",
        nargs="+",
        type=Path,
        help="Original images in the same order used by the analyzer.",
    )
    enrich.add_argument("-o", "--output", type=Path, help="Enriched JSON output path.")

    build = subparsers.add_parser("build", help="Generate and execute one CadQuery candidate.")
    build.add_argument("analysis", type=Path, help="Analyzer JSON artifact.")
    build.add_argument("--candidate-id", help="Immutable candidate identifier.")
    build.add_argument(
        "--candidate-root",
        type=Path,
        default=Path("artifacts/candidates"),
        help="Candidate output directory.",
    )
    build.add_argument("--revision-feedback", default="", help="Optional grader feedback.")
    build.add_argument(
        "--model",
        default=os.getenv(
            "VISION2STEP_BUILDER_MODEL",
            os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        ),
        help="Builder Claude model ID.",
    )
    build.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("VISION2STEP_BUILDER_MAX_TOKENS", "3000")),
        help="Maximum builder output tokens (default: 3000).",
    )
    build.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("VISION2STEP_CAD_TIMEOUT", "120")),
        help="CadQuery subprocess timeout in seconds (default: 120).",
    )
    build.add_argument(
        "--proposal-only",
        action="store_true",
        help="Save Builder Claude output without invoking the CAD executor.",
    )

    execute_source = subparsers.add_parser(
        "execute-source",
        help="Build a retained model.py without making a Claude API request.",
    )
    execute_source.add_argument("source", type=Path, help="Restricted CadQuery Python source.")
    execute_source.add_argument(
        "--candidate-id",
        required=True,
        help="Candidate identifier. A failed candidate with this ID is archived automatically.",
    )
    execute_source.add_argument(
        "--candidate-root",
        type=Path,
        default=Path("artifacts/candidates"),
        help="Candidate output directory.",
    )
    execute_source.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("VISION2STEP_CAD_TIMEOUT", "120")),
        help="CadQuery subprocess timeout in seconds (default: 120).",
    )
    return parser


def _run_analyze(args: argparse.Namespace) -> int:
    if args.max_tokens < 1000:
        raise Vision2StepError("--max-tokens must be at least 1000.")

    config = AnalyzerConfig(
        model=args.model,
        max_tokens=args.max_tokens,
        preferred_unit=Unit(args.unit),
    )
    artifact = VisionAnalyzer(config=config).analyze(args.images, object_context=args.context)
    output = args.output or Path("artifacts") / f"{args.images[0].stem}-analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

    total_tokens = artifact.token_usage.input_tokens + artifact.token_usage.output_tokens
    print(f"Analysis written to {output}")
    print(f"Model: {artifact.model} | Total tokens: {total_tokens}")
    return 0


def _run_build(args: argparse.Namespace) -> int:
    if args.max_tokens < 1000:
        raise Vision2StepError("--max-tokens must be at least 1000.")
    if not args.analysis.is_file():
        raise Vision2StepError(f"Analysis artifact does not exist: {args.analysis}")

    analysis = AnalysisArtifact.model_validate_json(args.analysis.read_text(encoding="utf-8"))
    candidate_id = args.candidate_id or f"candidate_{analysis.analysis_id[:8]}_001"
    builder = CadBuilder(config=BuilderConfig(model=args.model, max_tokens=args.max_tokens))
    artifact = builder.propose(analysis, revision_feedback=args.revision_feedback)

    if args.proposal_only:
        proposal_dir = args.candidate_root / "proposals"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        output = proposal_dir / f"{candidate_id}.json"
        if output.exists():
            raise Vision2StepError(f"Proposal already exists: {candidate_id}")
        output.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        print(f"Builder proposal written to {output}")
    else:
        result = execute_builder_artifact(
            artifact,
            candidate_id=candidate_id,
            candidate_root=args.candidate_root,
            timeout_seconds=args.timeout,
        )
        print(f"Valid STEP candidate written to {args.candidate_root / candidate_id}")
        print(f"Dimensions (mm): {result['metrics']['dimensions_mm']}")

    total_tokens = artifact.token_usage.input_tokens + artifact.token_usage.output_tokens
    print(f"Builder model: {artifact.model} | Total tokens: {total_tokens}")
    return 0


def _run_enrich(args: argparse.Namespace) -> int:
    if not args.analysis.is_file():
        raise Vision2StepError(f"Analysis artifact does not exist: {args.analysis}")
    analysis = AnalysisArtifact.model_validate_json(args.analysis.read_text(encoding="utf-8"))
    enriched = enrich_analysis_geometry(analysis, args.images)
    output = args.output or args.analysis.with_name(f"{args.analysis.stem}-enriched.json")
    if output.exists():
        raise Vision2StepError(f"Enriched artifact already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(enriched.model_dump_json(indent=2), encoding="utf-8")
    print(f"Enriched analysis written to {output}")
    print(f"Persisted geometry hint records: {len(enriched.geometry_hints)}")
    return 0


def _run_execute_source(args: argparse.Namespace) -> int:
    if not args.source.is_file():
        raise Vision2StepError(f"CadQuery source does not exist: {args.source}")
    if args.timeout < 1:
        raise Vision2StepError("--timeout must be at least 1 second.")

    # Read before build_candidate so a source inside a failed candidate remains available
    # when that candidate directory is archived for the retry.
    source = args.source.read_text(encoding="utf-8")
    result = execute_cadquery_source(
        source,
        candidate_id=args.candidate_id,
        candidate_root=args.candidate_root,
        timeout_seconds=args.timeout,
    )
    output = args.candidate_root / args.candidate_id
    print(f"Valid STEP candidate written to {output}")
    print(f"Dimensions (mm): {result['metrics']['dimensions_mm']}")
    print("Claude API calls: 0")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""

    try:
        try:
            from dotenv import load_dotenv
        except ImportError:
            pass
        else:
            load_dotenv()
        args = _build_parser().parse_args(argv)
        if args.command == "analyze":
            return _run_analyze(args)
        if args.command == "enrich":
            return _run_enrich(args)
        if args.command == "build":
            return _run_build(args)
        if args.command == "execute-source":
            return _run_execute_source(args)
        raise Vision2StepError(f"Unknown command: {args.command}")
    except Vision2StepError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
