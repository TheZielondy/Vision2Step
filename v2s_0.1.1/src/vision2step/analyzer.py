"""Claude-backed reference-image analyzer."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any, Sequence

from vision2step.errors import AnalyzerResponseError, Vision2StepError
from vision2step.geometry_hints import extract_geometry_hints
from vision2step.image_input import EncodedImage
from vision2step.models import (
    AnalysisArtifact,
    CADObjectSpecification,
    TokenUsage,
    Unit,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 3500


@dataclass(frozen=True)
class AnalyzerConfig:
    """Runtime options for one analyzer request."""

    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    preferred_unit: Unit = Unit.MILLIMETER

    @classmethod
    def from_environment(cls) -> AnalyzerConfig:
        raw_max_tokens = os.getenv("VISION2STEP_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
        try:
            max_tokens = int(raw_max_tokens)
        except ValueError as exc:
            raise Vision2StepError("VISION2STEP_MAX_TOKENS must be an integer.") from exc
        if max_tokens < 1000:
            raise Vision2StepError("VISION2STEP_MAX_TOKENS must be at least 1000.")

        return cls(
            model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
            max_tokens=max_tokens,
        )


def _load_system_prompt() -> str:
    prompt_file = files("vision2step.prompts").joinpath("vision_analyzer.md")
    return prompt_file.read_text(encoding="utf-8")


class VisionAnalyzer:
    """Convert one or more reference images into a validated CAD specification."""

    def __init__(self, client: Any | None = None, config: AnalyzerConfig | None = None) -> None:
        self.config = config or AnalyzerConfig.from_environment()
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

    def analyze(
        self,
        image_paths: Sequence[str | Path],
        *,
        object_context: str = "",
    ) -> AnalysisArtifact:
        """Analyze images in a single request and return a provenance-wrapped artifact."""

        if not image_paths:
            raise Vision2StepError("At least one reference image is required.")

        images = [EncodedImage.from_path(path) for path in image_paths]
        content = self._build_content(images, object_context)
        try:
            response = self.client.messages.parse(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=_load_system_prompt(),
                messages=[{"role": "user", "content": content}],
                output_format=CADObjectSpecification,
            )
        except Exception as exc:
            if exc.__class__.__module__.startswith("anthropic"):
                raise AnalyzerResponseError(f"Claude API request failed: {exc}") from exc
            raise

        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            raise AnalyzerResponseError("Claude refused to analyze the supplied image.")
        if stop_reason == "max_tokens":
            raise AnalyzerResponseError(
                "Claude reached the output limit before completing the specification. "
                "Increase --max-tokens and retry."
            )

        parsed = getattr(response, "parsed_output", None)
        if parsed is None:
            raise AnalyzerResponseError("Claude returned no structured specification.")
        if not isinstance(parsed, CADObjectSpecification):
            parsed = CADObjectSpecification.model_validate(parsed)

        usage = getattr(response, "usage", None)
        return AnalysisArtifact(
            artifact_version="1.2",
            analysis_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC).isoformat(),
            model=self.config.model,
            response_id=str(getattr(response, "id", "unknown")),
            source_images=[image.source_metadata() for image in images],
            token_usage=TokenUsage(
                input_tokens=int(getattr(usage, "input_tokens", 0)),
                output_tokens=int(getattr(usage, "output_tokens", 0)),
            ),
            specification=parsed,
        )

    def _build_content(
        self,
        images: Sequence[EncodedImage],
        object_context: str,
    ) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = []
        for index, image in enumerate(images, start=1):
            if len(images) > 1:
                content.append({"type": "text", "text": f"Reference image {index}:"})
            content.append(image.as_content_block())

        measurement_reports: list[str] = []
        for index, image in enumerate(images, start=1):
            try:
                hints = extract_geometry_hints(image.data)
            except Exception:
                hints = None
            if hints is not None:
                measurement_reports.append(hints.as_prompt_text(index))
        if measurement_reports:
            content.append(
                {
                    "type": "text",
                    "text": (
                        "Local deterministic measurements follow. Treat them as geometric "
                        "evidence when segmentation confidence is medium or high. They are "
                        "normalized measurements, not semantic interpretations.\n\n"
                        + "\n\n".join(measurement_reports)
                    ),
                }
            )

        context = object_context.strip() or "No dimensions or object context were supplied."
        content.append(
            {
                "type": "text",
                "text": (
                    "Analyze the supplied reference image set as input to a parametric CAD "
                    "construction workflow.\n"
                    f"Preferred unit: {self.config.preferred_unit.value}\n"
                    f"User-supplied context: {context}"
                ),
            }
        )
        return content
