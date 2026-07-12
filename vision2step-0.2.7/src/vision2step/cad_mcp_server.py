"""Local FastMCP server exposing restricted Vision2STEP CAD operations."""

from __future__ import annotations

import json
from typing import Any

from vision2step.cad_execution import CadExecutionService


def _json_result(operation: str, callback: Any) -> str:
    try:
        result = callback()
        return json.dumps({"operation": operation, "ok": True, "result": result})
    except Exception as exc:
        return json.dumps({"operation": operation, "ok": False, "error": str(exc)})


def create_server() -> Any:
    """Create the server lazily so analyzer-only installs do not require MCP."""

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError('Install CAD dependencies with `pip install -e ".[cad]"`.') from exc

    service = CadExecutionService.from_environment()
    mcp = FastMCP("Vision2STEP CAD", log_level="ERROR")

    @mcp.tool()
    def build_candidate(candidate_id: str, cadquery_source: str) -> str:
        """Validate restricted CadQuery source, create an immutable candidate, and export STEP."""

        return _json_result(
            "build_candidate",
            lambda: service.build_candidate(candidate_id, cadquery_source),
        )

    @mcp.tool()
    def validate_step(candidate_id: str) -> str:
        """Reopen a candidate STEP file in a fresh CAD subprocess and return validity metrics."""

        return _json_result("validate_step", lambda: service.validate_step(candidate_id))

    @mcp.tool()
    def inspect_model(candidate_id: str) -> str:
        """Read the saved dimensions, volume, area, solid count, and validity metrics."""

        return _json_result("inspect_model", lambda: service.inspect_model(candidate_id))

    @mcp.tool()
    def list_candidate_artifacts(candidate_id: str) -> str:
        """List the immutable files currently stored for a candidate."""

        return _json_result(
            "list_candidate_artifacts",
            lambda: service.list_candidate_artifacts(candidate_id),
        )

    return mcp


def main() -> None:
    """Run the local server over the standard stdio transport."""

    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
