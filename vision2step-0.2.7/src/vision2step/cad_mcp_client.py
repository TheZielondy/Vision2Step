"""Small stdio client used by the deterministic Step 2 controller."""

from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, cast

from vision2step.errors import CandidateExecutionError
from vision2step.runtime_environment import sanitized_runtime_environment


class CadMCPClient:
    """Connect to the bundled CAD MCP server and call JSON-returning tools."""

    def __init__(self, candidate_root: str | Path, *, timeout_seconds: int = 120) -> None:
        self.candidate_root = Path(candidate_root).expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self._exit_stack = AsyncExitStack()
        self._session: Any | None = None

    async def connect(self) -> None:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise CandidateExecutionError(
                'Install CAD dependencies with `pip install -e ".[cad]"`.'
            ) from exc

        environment = sanitized_runtime_environment()
        environment["VISION2STEP_CANDIDATE_ROOT"] = str(self.candidate_root)
        environment["VISION2STEP_CAD_TIMEOUT"] = str(self.timeout_seconds)
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "vision2step.cad_mcp_server"],
            env=environment,
        )
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(parameters)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        self._session = session
        await session.initialize()

    async def call_json(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._session is None:
            raise CandidateExecutionError("CAD MCP client is not connected.")
        result = await self._session.call_tool(tool_name, arguments)
        for block in result.content:
            text = getattr(block, "text", None)
            if text:
                try:
                    return cast(dict[str, Any], json.loads(text))
                except json.JSONDecodeError:
                    continue
        raise CandidateExecutionError(f"MCP tool returned no JSON result: {tool_name}")

    async def close(self) -> None:
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self) -> CadMCPClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.close()
