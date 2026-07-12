# CadQuery builder and MCP tools

## Builder source contract

Builder Claude must return one structured proposal and a source string that:

- imports exactly `cadquery as cq`;
- declares editable numeric parameters near the top;
- uses linear CadQuery expressions;
- assigns the completed object to `result`;
- produces one Workplane or Shape containing exactly one solid;
- performs no export or external I/O.
- performs `union`, `cut`, and `intersect` only between solids, never between unextruded profiles.

The allowlist is defined in `src/vision2step/source_policy.py`. When a useful CadQuery
operation is missing, add it deliberately with a focused policy test rather than weakening
the validator broadly.

For a planar object, either keep the outer wire and enclosed hole wires on one Workplane and
extrude once, or extrude separate component profiles before using a solid boolean operation.

## MCP tools

### `build_candidate`

Input:

- `candidate_id`
- `cadquery_source`

Output includes status and geometric metrics. Source-policy failures occur before a
candidate directory is created. Runtime failures preserve `model.py` and a failed manifest.

### `validate_step`

Reimports an existing candidate STEP file in a new subprocess. This does not trust the
metrics saved during the original build.

### `inspect_model`

Returns the saved metric record without rerunning OpenCascade.

### `list_candidate_artifacts`

Returns candidate filenames and byte sizes without exposing arbitrary filesystem paths.

## Repair workflow

Re-execute retained source without Claude when the source itself is expected to be valid:

```bat
python -m vision2step execute-source artifacts\candidates\part_001\model.py ^
  --candidate-id part_001
```

For a genuine modeling error, copy the execution error into a new build request:

```bat
vision2step build artifacts\part-analysis.json \
  --candidate-id part_002 \
  --revision-feedback "Previous candidate failed: <error text>"
```

Successful candidate IDs remain immutable. Failed candidate IDs are archived automatically and
may be reused by `execute-source` or a corrected build.
