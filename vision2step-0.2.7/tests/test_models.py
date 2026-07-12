"""Tests for the analyzer's public data contract."""

from __future__ import annotations

import json
import unittest

from pydantic import ValidationError

from tests.helpers import example_artifact
from vision2step.models import BuilderProposal


class ModelContractTests(unittest.TestCase):
    def test_illustrative_artifact_matches_contract(self) -> None:
        artifact = example_artifact()

        self.assertEqual(artifact.specification.schema_version, "1.2")
        self.assertEqual(artifact.specification.components[0].component_id, "bracket_body")
        self.assertTrue(artifact.model_dump_json())

    def test_claude_output_schema_stays_small(self) -> None:
        artifact = example_artifact()
        schema = artifact.specification.__class__.model_json_schema()

        self.assertLess(len(json.dumps(schema)), 7000)

    def test_builder_output_schema_stays_small(self) -> None:
        schema = BuilderProposal.model_json_schema()

        self.assertLess(len(json.dumps(schema)), 3000)

    def test_unknown_fields_are_rejected(self) -> None:
        artifact = example_artifact().model_dump()
        artifact["unexpected"] = True

        with self.assertRaises(ValidationError):
            type(example_artifact()).model_validate(artifact)


if __name__ == "__main__":
    unittest.main()
