"""Validated data contracts shared by the vision analyzer and future CAD stages."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects undeclared fields at every schema level."""

    model_config = ConfigDict(extra="forbid")


class Unit(StrEnum):
    """Units accepted by the command-line interface."""

    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    INCH = "in"
    RELATIVE = "relative"


class CADComponent(StrictModel):
    """One independently describable part of the visible object."""

    component_id: str = Field(description="Stable snake_case identifier.")
    parent_component_id: str = Field(description="Parent ID, or an empty string for root.")
    name: str
    geometry: str = Field(description="Shape, silhouette, cross-section, and visible surfaces.")
    cad_strategy: str = Field(description="Likely sketch and CadQuery construction operations.")
    dimensions: list[str] = Field(
        description="Dimension estimates with value/range, unit, evidence status, and confidence."
    )
    pose: str = Field(description="Position, orientation, symmetry, and relation to the origin.")
    evidence_status: str = Field(description="Use observed, inferred, or unknown.")
    confidence: str = Field(description="Use high, medium, or low.")


class CADFeature(StrictModel):
    """One local additive, subtractive, finishing, or reference feature."""

    feature_id: str = Field(description="Stable snake_case identifier.")
    target_component_id: str
    feature_type: str = Field(description="CAD operation such as hole, pocket, boss, or fillet.")
    description: str
    parameters: list[str] = Field(
        description="Parameter estimates with unit, evidence status, and confidence."
    )
    evidence_status: str = Field(description="Use observed, inferred, or unknown.")
    confidence: str = Field(description="Use high, medium, or low.")


class CADObjectSpecification(StrictModel):
    """Lean builder-ready interpretation designed to fit Claude's grammar limits."""

    schema_version: str = Field(description="Always 1.2 for this contract.")
    summary: str
    object_name: str
    category: str
    overall_confidence: str = Field(description="Use high, medium, or low.")
    modeling_class: str = Field(
        description="Examples: planar_extrusion, revolved, prismatic, assembled, or freeform."
    )
    coordinate_system: str = Field(
        description="Unit, scale basis, origin, and meanings of positive X, Y, and Z."
    )
    overall_dimensions: list[str] = Field(
        description="Overall dimension estimates including ranges, evidence, and confidence."
    )
    camera_estimate: str = Field(
        description="Projection, azimuth, elevation, roll, focal character, target, and confidence."
    )
    observed_geometry: list[str]
    inferred_geometry: list[str]
    unknown_geometry: list[str]
    components: list[CADComponent]
    features: list[CADFeature]
    assumptions: list[str]
    clarification_questions: list[str]
    build_strategy: list[str] = Field(
        description="Ordered, dependency-aware CadQuery construction steps with risks."
    )
    evaluation_anchors: list[str] = Field(
        description="Visible properties a later grader should compare, including importance/view."
    )


class SourceImage(StrictModel):
    """Reproducibility metadata for one locally supplied image."""

    file_name: str
    media_type: str
    byte_size: int
    sha256: str


class TokenUsage(StrictModel):
    """Token accounting returned by the Claude API."""

    input_tokens: int
    output_tokens: int


class EnclosedRegionHint(StrictModel):
    """Normalized enclosed background region measured without Claude."""

    center_x: float
    center_y: float
    width: float
    height: float
    area_fraction: float


class GeometryHintRecord(StrictModel):
    """Persisted local image measurements used as higher-priority builder evidence."""

    image_number: int
    file_name: str
    raster_width: int
    raster_height: int
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    object_aspect_ratio: float
    dominant_axis: str
    foreground_fill_ratio: float
    enclosed_regions: list[EnclosedRegionHint]
    confidence: str


class AnalysisArtifact(StrictModel):
    """Saved analyzer output with provenance and its CAD object specification."""

    artifact_version: Literal["1.2", "1.3"]
    analysis_id: str
    generated_at: str
    model: str
    response_id: str
    source_images: list[SourceImage]
    geometry_hints: list[GeometryHintRecord] = Field(default_factory=list)
    token_usage: TokenUsage
    specification: CADObjectSpecification


class BuilderProposal(StrictModel):
    """Independent Builder Claude output before any local execution."""

    schema_version: str = Field(description="Always 1.0 for this contract.")
    candidate_name: str = Field(description="Short snake_case candidate label.")
    modeling_summary: str
    evidence_used: list[str]
    contradictions_resolved: list[str]
    assumptions_used: list[str]
    optional_features_omitted: list[str]
    expected_dimensions: list[str]
    cadquery_source: str = Field(
        description="Complete restricted Python source defining a CadQuery object named result."
    )


class BuilderArtifact(StrictModel):
    """Saved provenance wrapper for a Builder Claude proposal."""

    artifact_version: Literal["1.0"]
    build_id: str
    generated_at: str
    model: str
    response_id: str
    source_analysis_id: str
    token_usage: TokenUsage
    proposal: BuilderProposal
