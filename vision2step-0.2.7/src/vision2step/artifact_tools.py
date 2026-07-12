"""Token-free transformations for existing Vision2STEP artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from vision2step.errors import Vision2StepError
from vision2step.geometry_hints import extract_geometry_hints
from vision2step.image_input import EncodedImage
from vision2step.models import AnalysisArtifact


def enrich_analysis_geometry(
    artifact: AnalysisArtifact,
    image_paths: Sequence[str | Path],
) -> AnalysisArtifact:
    """Persist local geometry hints in an existing report without another Claude call."""

    if len(image_paths) != len(artifact.source_images):
        raise Vision2StepError(
            "The number of reference images must match the analyzer artifact."
        )

    records = []
    for index, (image_path, expected) in enumerate(
        zip(image_paths, artifact.source_images, strict=True),
        start=1,
    ):
        image = EncodedImage.from_path(image_path)
        actual = image.source_metadata()
        if actual.sha256 != expected.sha256:
            raise Vision2StepError(
                f"Reference image {index} does not match the artifact SHA-256 hash."
            )
        hints = extract_geometry_hints(image.data)
        if hints is not None:
            records.append(hints.as_record(index, actual.file_name))

    data = artifact.model_dump()
    data["artifact_version"] = "1.3"
    data["geometry_hints"] = [record.model_dump() for record in records]
    return AnalysisArtifact.model_validate(data)
