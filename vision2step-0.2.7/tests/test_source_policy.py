"""Tests for the restricted CadQuery source language."""

from __future__ import annotations

import unittest

from vision2step.errors import SourcePolicyError
from vision2step.source_policy import validate_cadquery_source

VALID_SOURCE = """import cadquery as cq
LENGTH = 120.0
WIDTH = 60.0
THICKNESS = 10.0
result = cq.Workplane("XY").box(LENGTH, WIDTH, THICKNESS)
"""


class SourcePolicyTests(unittest.TestCase):
    def test_linear_cadquery_source_is_accepted(self) -> None:
        report = validate_cadquery_source(VALID_SOURCE)

        self.assertEqual(report.imports, ("cadquery",))
        self.assertGreater(report.node_count, 0)

    def test_radius_arc_is_accepted(self) -> None:
        source = """import cadquery as cq
RADIUS = 5.0
result = (
    cq.Workplane("XY")
    .moveTo(0, -RADIUS)
    .radiusArc((RADIUS, 0), RADIUS)
    .lineTo(0, 0)
    .close()
    .extrude(2.0)
)
"""

        report = validate_cadquery_source(source)

        self.assertGreater(report.node_count, 0)

    def test_sketch_finalize_is_accepted(self) -> None:
        source = """import cadquery as cq
result = (
    cq.Workplane("XY")
    .placeSketch(cq.Sketch().slot(40.0, 12.0).finalize())
    .extrude(2.0)
)
"""

        report = validate_cadquery_source(source)

        self.assertGreater(report.node_count, 0)

    def test_boolean_between_unextruded_profiles_is_rejected(self) -> None:
        source = """import cadquery as cq
outer_profile = cq.Workplane("XY").rect(60.0, 30.0)
handle_profile = cq.Workplane("XY").rect(20.0, 8.0)
combined_profile = outer_profile.union(handle_profile)
hole_profile = cq.Workplane("XY").ellipse(2.0, 4.0)
final_profile = combined_profile.cut(hole_profile)
result = final_profile.extrude(5.0, both=True)
"""

        with self.assertRaisesRegex(SourcePolicyError, "unextruded 2D profile"):
            validate_cadquery_source(source)

    def test_boolean_between_extruded_solids_is_accepted(self) -> None:
        source = """import cadquery as cq
body = cq.Workplane("XY").rect(60.0, 30.0).extrude(5.0, both=True)
handle = cq.Workplane("XY").center(30.0, 0.0).rect(20.2, 8.0).extrude(5.0, both=True)
combined = body.union(handle)
result = combined.faces(">Z").workplane().center(35.0, 0.0).ellipse(2.0, 4.0).cutThruAll()
"""

        report = validate_cadquery_source(source)

        self.assertGreater(report.node_count, 0)

    def test_file_access_is_rejected(self) -> None:
        source = VALID_SOURCE + '\ncontent = open("secret.txt").read()\n'

        with self.assertRaises(SourcePolicyError):
            validate_cadquery_source(source)

    def test_other_import_is_rejected(self) -> None:
        with self.assertRaises(SourcePolicyError):
            validate_cadquery_source("import os\nresult = 1\n")

    def test_functions_are_rejected(self) -> None:
        source = """import cadquery as cq
def build():
    return cq.Workplane("XY").box(1, 1, 1)
result = build()
"""
        with self.assertRaises(SourcePolicyError):
            validate_cadquery_source(source)


if __name__ == "__main__":
    unittest.main()
