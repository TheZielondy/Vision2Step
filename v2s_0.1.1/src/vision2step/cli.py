"""Command-line interface for the implemented Vision2STEP stages."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from vision2step.analyzer import AnalyzerConfig, VisionAnalyzer
from vision2step.errors import Vision2StepError
from vision2step.models import Unit


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vision2step",
        description="Convert reference images into CAD-ready structured specifications.",
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""

    try:
        try:
            from dotenv import load_dotenv
        except ImportError:
            load_dotenv = None

        if load_dotenv is not None:
            load_dotenv()
        args = _build_parser().parse_args(argv)
        if args.command == "analyze":
            return _run_analyze(args)
        raise Vision2StepError(f"Unknown command: {args.command}")
    except Vision2StepError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
