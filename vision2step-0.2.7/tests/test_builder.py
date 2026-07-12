"""Offline tests for the independent Builder Claude request."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from tests.helpers import example_artifact
from tests.test_source_policy import VALID_SOURCE
from vision2step.builder import BuilderConfig, CadBuilder
from vision2step.models import BuilderProposal


class FakeMessages:
    def __init__(self, proposal: BuilderProposal) -> None:
        self.proposal = proposal
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return SimpleNamespace(
            id="msg_builder_test",
            stop_reason="end_turn",
            parsed_output=self.proposal,
            usage=SimpleNamespace(input_tokens=500, output_tokens=250),
        )


class FakeClient:
    def __init__(self, proposal: BuilderProposal) -> None:
        self.messages = FakeMessages(proposal)


class CadBuilderTests(unittest.TestCase):
    def test_builder_uses_fresh_structured_request(self) -> None:
        proposal = BuilderProposal(
            schema_version="1.0",
            candidate_name="board_001",
            modeling_summary="Simple parameterized box candidate.",
            evidence_used=["Explicit dimensions"],
            contradictions_resolved=[],
            assumptions_used=["Thickness defaults to 10 mm"],
            optional_features_omitted=["Low-confidence edge fillet"],
            expected_dimensions=["120 x 60 x 10 mm"],
            cadquery_source=VALID_SOURCE,
        )
        client = FakeClient(proposal)
        artifact = CadBuilder(
            client=client,
            config=BuilderConfig(model="claude-sonnet-4-6", max_tokens=3000),
        ).propose(example_artifact())

        request = client.messages.kwargs
        self.assertEqual(len(request["messages"]), 1)
        self.assertIs(request["output_format"], BuilderProposal)
        self.assertIn("<analysis_artifact>", request["messages"][0]["content"])
        self.assertEqual(artifact.source_analysis_id, example_artifact().analysis_id)
        self.assertEqual(artifact.token_usage.output_tokens, 250)


if __name__ == "__main__":
    unittest.main()
