"""AST policy for the deliberately small CadQuery source language."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from vision2step.errors import SourcePolicyError

MAX_SOURCE_CHARACTERS = 30_000
MAX_AST_NODES = 2_500

ALLOWED_CALL_NAMES = {"abs", "float", "int", "max", "min", "round"}
ALLOWED_ATTRIBUTES = {
    "Workplane",
    "Vector",
    "Sketch",
    "add",
    "arc",
    "assemble",
    "box",
    "cboreHole",
    "center",
    "chamfer",
    "circle",
    "clean",
    "close",
    "combine",
    "cskHole",
    "cut",
    "cutBlind",
    "cutThruAll",
    "cylinder",
    "each",
    "edges",
    "ellipse",
    "extrude",
    "face",
    "faces",
    "fillet",
    "finalize",
    "hLine",
    "hLineTo",
    "hole",
    "intersect",
    "line",
    "lineTo",
    "loft",
    "mirrorX",
    "mirrorY",
    "move",
    "moveTo",
    "offset",
    "offset2D",
    "polarArray",
    "placeSketch",
    "polygon",
    "polyline",
    "push",
    "pushPoints",
    "radiusArc",
    "reset",
    "rarray",
    "regularPolygon",
    "rect",
    "revolve",
    "rotate",
    "rotateAboutCenter",
    "shell",
    "segment",
    "sketch",
    "slot",
    "solids",
    "sphere",
    "spline",
    "split",
    "sweep",
    "tangentArcPoint",
    "threePointArc",
    "toPending",
    "trapezoid",
    "translate",
    "transformed",
    "union",
    "vLine",
    "vLineTo",
    "vertices",
    "wires",
    "workplane",
}

ALLOWED_NODE_TYPES = {
    ast.Add,
    ast.alias,
    ast.AnnAssign,
    ast.Assign,
    ast.Attribute,
    ast.BinOp,
    ast.Call,
    ast.Constant,
    ast.Dict,
    ast.Div,
    ast.Expr,
    ast.FloorDiv,
    ast.Import,
    ast.keyword,
    ast.List,
    ast.Load,
    ast.Mod,
    ast.Module,
    ast.Mult,
    ast.Name,
    ast.Pow,
    ast.Store,
    ast.Sub,
    ast.Tuple,
    ast.UAdd,
    ast.UnaryOp,
    ast.USub,
}

PROFILE_METHODS = {
    "arc",
    "circle",
    "close",
    "ellipse",
    "hLine",
    "hLineTo",
    "line",
    "lineTo",
    "moveTo",
    "offset2D",
    "polygon",
    "polyline",
    "radiusArc",
    "rect",
    "regularPolygon",
    "spline",
    "tangentArcPoint",
    "threePointArc",
    "trapezoid",
    "vLine",
    "vLineTo",
}

SOLID_CREATION_METHODS = {
    "box",
    "cylinder",
    "extrude",
    "loft",
    "revolve",
    "sphere",
    "sweep",
}

SOLID_BOOLEAN_METHODS = {"cut", "intersect", "union"}
SOLID_CUT_METHODS = {"cboreHole", "cskHole", "cutBlind", "cutThruAll", "hole"}


@dataclass(frozen=True)
class SourcePolicyReport:
    """Summary recorded with each accepted candidate source file."""

    node_count: int
    source_characters: int
    imports: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "node_count": self.node_count,
            "source_characters": self.source_characters,
            "imports": list(self.imports),
        }


def _geometry_kind(node: ast.AST, variables: dict[str, str]) -> str:
    """Infer only the profile/solid distinction needed for safe boolean checks."""

    if isinstance(node, ast.Name):
        return variables.get(node.id, "unknown")
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return "unknown"

    method = node.func.attr
    receiver_kind = _geometry_kind(node.func.value, variables)
    if method in SOLID_CREATION_METHODS or method in SOLID_CUT_METHODS:
        return "solid"
    if method in PROFILE_METHODS:
        return "profile"
    if method in SOLID_BOOLEAN_METHODS:
        return "solid" if receiver_kind == "solid" else "unknown"
    if method == "Workplane":
        return "workplane"
    return receiver_kind


def _reject_profile_booleans(tree: ast.Module) -> None:
    """Reject OpenCascade booleans whose operands are still 2D profile wires."""

    variables: dict[str, str] = {}
    for statement in tree.body:
        value = getattr(statement, "value", None)
        if isinstance(value, ast.AST):
            for node in ast.walk(value):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in SOLID_BOOLEAN_METHODS
                ):
                    receiver_kind = _geometry_kind(node.func.value, variables)
                    argument_kinds = [_geometry_kind(argument, variables) for argument in node.args]
                    if receiver_kind == "profile" or "profile" in argument_kinds:
                        raise SourcePolicyError(
                            f"CadQuery `{node.func.attr}()` cannot operate on an unextruded "
                            "2D profile. Extrude each operand first, or place the outer and "
                            "enclosed wires on one Workplane and extrude once."
                        )

        if isinstance(statement, (ast.Assign, ast.AnnAssign)) and isinstance(value, ast.AST):
            kind = _geometry_kind(value, variables)
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    variables[target.id] = kind


def validate_cadquery_source(source: str) -> SourcePolicyReport:
    """Reject source outside the intentionally linear CadQuery subset."""

    if not source.strip():
        raise SourcePolicyError("CadQuery source is empty.")
    if len(source) > MAX_SOURCE_CHARACTERS:
        raise SourcePolicyError(f"CadQuery source exceeds {MAX_SOURCE_CHARACTERS} characters.")

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise SourcePolicyError(f"CadQuery source has invalid Python syntax: {exc}") from exc

    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise SourcePolicyError(f"CadQuery source exceeds {MAX_AST_NODES} AST nodes.")

    imports: list[str] = []
    result_assigned = False
    for node in nodes:
        if type(node) not in ALLOWED_NODE_TYPES:
            raise SourcePolicyError(f"Python construct is not allowed: {type(node).__name__}.")

        if isinstance(node, ast.Import):
            if len(node.names) != 1:
                raise SourcePolicyError("Only `import cadquery as cq` is allowed.")
            alias = node.names[0]
            if alias.name != "cadquery" or alias.asname != "cq":
                raise SourcePolicyError("Only `import cadquery as cq` is allowed.")
            imports.append(alias.name)

        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise SourcePolicyError("Dunder names are not allowed.")

        if isinstance(node, ast.Attribute) and (
            node.attr.startswith("_") or node.attr not in ALLOWED_ATTRIBUTES
        ):
            raise SourcePolicyError(f"CadQuery attribute is not allowed: {node.attr}.")

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id not in ALLOWED_CALL_NAMES
        ):
            raise SourcePolicyError(f"Function call is not allowed: {node.func.id}.")

        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id == "result":
                    result_assigned = True

    if imports != ["cadquery"]:
        raise SourcePolicyError("Source must contain exactly `import cadquery as cq`.")
    if not result_assigned:
        raise SourcePolicyError("Source must assign the final CadQuery object to `result`.")

    _reject_profile_booleans(tree)

    return SourcePolicyReport(
        node_count=len(nodes),
        source_characters=len(source),
        imports=tuple(imports),
    )
