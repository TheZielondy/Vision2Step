"""Isolated subprocess entry point for building and inspecting STEP candidates."""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from vision2step.source_policy import validate_cadquery_source

STAGE_FILE_NAME = "last-stage.txt"


def _report_stage(stage: str) -> None:
    print(f"vision2step-stage:{stage}", file=sys.stderr, flush=True)
    # Stderr remains the primary channel; the file is a Windows timeout fallback.
    with contextlib.suppress(OSError):
        Path(STAGE_FILE_NAME).write_text(stage + "\n", encoding="utf-8")


def _execute_source_statement_by_statement(
    source: str, script_path: Path, namespace: dict[str, Any]
) -> None:
    tree = ast.parse(source, filename=str(script_path))
    for index, statement in enumerate(tree.body, start=1):
        start_line = int(getattr(statement, "lineno", 0))
        end_line = int(getattr(statement, "end_lineno", start_line))
        _report_stage(f"source_statement_{index}_lines_{start_line}-{end_line}")
        statement_module = ast.Module(body=[statement], type_ignores=[])
        ast.fix_missing_locations(statement_module)
        exec(compile(statement_module, str(script_path), "exec"), namespace, namespace)


def _safe_import(
    name: str,
    globals_: dict[str, Any] | None = None,
    locals_: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    del globals_, locals_, fromlist, level
    if name != "cadquery":
        raise ImportError(f"Import is not allowed: {name}")
    return importlib.import_module("cadquery")


def _restricted_builtins() -> dict[str, Any]:
    return {
        "__import__": _safe_import,
        "abs": abs,
        "float": float,
        "int": int,
        "max": max,
        "min": min,
        "round": round,
    }


def _shape_metrics(shape: Any) -> dict[str, Any]:
    bounding_box = shape.BoundingBox()
    solids = list(shape.Solids())
    solid_count = len(solids) or (1 if shape.ShapeType() == "Solid" else 0)
    return {
        "valid": bool(shape.isValid()),
        "shape_type": str(shape.ShapeType()),
        "solid_count": solid_count,
        "dimensions_mm": {
            "x": float(bounding_box.xlen),
            "y": float(bounding_box.ylen),
            "z": float(bounding_box.zlen),
        },
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
    }


def _require_single_valid_solid(metrics: dict[str, Any], *, source: str) -> None:
    if (
        not metrics["valid"]
        or metrics["solid_count"] != 1
        or metrics["volume_mm3"] <= 0
    ):
        raise ValueError(
            f"{source} must contain exactly one valid solid with positive volume; "
            f"found {metrics['solid_count']} solids."
        )


def build(script_path: Path, step_path: Path) -> dict[str, Any]:
    _report_stage("source_validation")
    source = script_path.read_text(encoding="utf-8")
    validate_cadquery_source(source)
    namespace: dict[str, Any] = {"__builtins__": _restricted_builtins()}
    _report_stage("cadquery_import")
    cq = importlib.import_module("cadquery")
    _report_stage("source_execution")
    _execute_source_statement_by_statement(source, script_path, namespace)

    result = namespace.get("result")
    if isinstance(result, cq.Workplane):
        shape = result.val()
    elif isinstance(result, cq.Shape):
        shape = result
    else:
        raise TypeError("`result` must be a CadQuery Workplane or Shape.")

    _report_stage("geometry_metrics")
    metrics = _shape_metrics(shape)
    _require_single_valid_solid(metrics, source="Candidate")

    _report_stage("step_export")
    cq.exporters.export(result, str(step_path), exportType="STEP")
    _report_stage("step_reimport")
    reopened = cq.importers.importStep(str(step_path)).val()
    _report_stage("reopened_metrics")
    reopened_metrics = _shape_metrics(reopened)
    metrics["step_reopened"] = True
    metrics["step_reopened_valid"] = reopened_metrics["valid"]
    metrics["step_reopened_solid_count"] = reopened_metrics["solid_count"]
    _require_single_valid_solid(reopened_metrics, source="Reopened STEP")
    _report_stage("complete")
    Path(STAGE_FILE_NAME).unlink(missing_ok=True)
    return metrics


def inspect_step(step_path: Path) -> dict[str, Any]:
    _report_stage("step_inspect_import")
    cq = importlib.import_module("cadquery")
    shape = cq.importers.importStep(str(step_path)).val()
    _report_stage("step_inspect_metrics")
    metrics = _shape_metrics(shape)
    metrics["step_reopened"] = True
    metrics["step_reopened_valid"] = metrics["valid"]
    _report_stage("complete")
    Path(STAGE_FILE_NAME).unlink(missing_ok=True)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("script", type=Path)
    build_parser.add_argument("step", type=Path)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("step", type=Path)
    args = parser.parse_args()

    result = (
        build(args.script, args.step)
        if args.command == "build"
        else inspect_step(args.step)
    )
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
