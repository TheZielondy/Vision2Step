"""Independent Claude builder that proposes restricted CadQuery source."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

from vision2step.errors import BuilderResponseError, Vision2StepError
from vision2step.models import AnalysisArtifact, BuilderArtifact, BuilderProposal, TokenUsage

DEFAULT_BUILDER_MODEL = "claude-sonnet-4-6"
DEFAULT_BUILDER_MAX_TOKENS = 3000


@dataclass(frozen=True)
class BuilderConfig:
    """Runtime options for one independent builder request."""

    model: str = DEFAULT_BUILDER_MODEL
    max_tokens: int = DEFAULT_BUILDER_MAX_TOKENS

    @classmethod
    def from_environment(cls) -> BuilderConfig:
        raw_max_tokens = os.getenv(
            "VISION2STEP_BUILDER_MAX_TOKENS", str(DEFAULT_BUILDER_MAX_TOKENS)
        )
        try:
            max_tokens = int(raw_max_tokens)
        except ValueError as exc:
            raise Vision2StepError("VISION2STEP_BUILDER_MAX_TOKENS must be an integer.") from exc
        if max_tokens < 1000:
            raise Vision2StepError("VISION2STEP_BUILDER_MAX_TOKENS must be at least 1000.")
        return cls(
            model=os.getenv(
                "VISION2STEP_BUILDER_MODEL",
                os.getenv("ANTHROPIC_MODEL", DEFAULT_BUILDER_MODEL),
            ),
            max_tokens=max_tokens,
        )


def _load_builder_prompt() -> str:
    prompt_file = files("vision2step.prompts").joinpath("cad_builder.md")
    return prompt_file.read_text(encoding="utf-8")


class CadBuilder:
    """Generate a CadQuery proposal in a fresh Claude context."""

    def __init__(self, client: Any | None = None, config: BuilderConfig | None = None) -> None:
        self.config = config or BuilderConfig.from_environment()
        self.client = client or self._create_client()

    @staticmethod
    def _create_client() -> Any:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise Vision2StepError(
                "The Anthropic SDK is not installed. Run `pip install -e .` first."
            ) from exc
        try:
            return Anthropic()
        except Exception as exc:
            raise Vision2StepError(
                "Could not initialize the Anthropic client. Check ANTHROPIC_API_KEY."
            ) from exc

    def propose(
        self,
        analysis: AnalysisArtifact,
        *,
        revision_feedback: str = "",
    ) -> BuilderArtifact:
        """Generate one proposal without inheriting the analyzer conversation."""

        feedback = revision_feedback.strip() or "No previous candidate feedback was supplied."
        user_prompt = (
            "Create one restricted CadQuery candidate from the analyzer artifact below.\n\n"
            "<analysis_artifact>\n"
            f"{analysis.model_dump_json(indent=2)}\n"
            "</analysis_artifact>\n\n"
            "<revision_feedback>\n"
            f"{feedback}\n"
            "</revision_feedback>"
        )
        try:
            response = self.client.messages.parse(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=_load_builder_prompt(),
                messages=[{"role": "user", "content": user_prompt}],
                output_format=BuilderProposal,
            )
        except Exception as exc:
            if exc.__class__.__module__.startswith("anthropic"):
                raise BuilderResponseError(f"Builder Claude request failed: {exc}") from exc
            raise

        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            raise BuilderResponseError("Builder Claude refused to create a candidate.")
        if stop_reason == "max_tokens":
            raise BuilderResponseError(
                "Builder Claude reached the output limit. Increase the builder token limit."
            )

        parsed = getattr(response, "parsed_output", None)
        if parsed is None:
            raise BuilderResponseError("Builder Claude returned no structured proposal.")
        if not isinstance(parsed, BuilderProposal):
            parsed = BuilderProposal.model_validate(parsed)

        usage = getattr(response, "usage", None)
        return BuilderArtifact(
            artifact_version="1.0",
            build_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC).isoformat(),
            model=self.config.model,
            response_id=str(getattr(response, "id", "unknown")),
            source_analysis_id=analysis.analysis_id,
            token_usage=TokenUsage(
                input_tokens=int(getattr(usage, "input_tokens", 0)),
                output_tokens=int(getattr(usage, "output_tokens", 0)),
            ),
            proposal=parsed,
        )
