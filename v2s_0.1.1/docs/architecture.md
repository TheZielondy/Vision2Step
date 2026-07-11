# Vision analyzer architecture

This milestone implements one bounded workflow stage. It does not contain placeholder CAD
generation disguised as finished functionality.

## Data flow

1. The CLI receives one or more local image paths and optional object context.
2. `EncodedImage` validates the file signature, enforces the API size limit, and prepares
   the base64 image block.
3. A local Pillow pass conservatively measures foreground bounds, aspect ratio, dominant
   image axis, and enclosed background regions. It sends normalized hints, not semantic
   conclusions, and therefore consumes no additional model-generation tokens.
4. `VisionAnalyzer` places the visual evidence before the detailed user request and sends
   one Claude Messages API call.
5. Claude is constrained to `CADObjectSpecification` through structured outputs.
6. Pydantic rejects undeclared or invalid fields.
7. The specification is wrapped in `AnalysisArtifact`, adding image hashes, model identity,
   response identity, timestamp, and token usage.
8. The CLI writes one portable JSON artifact for the next workflow stage.

## Design boundaries

The analyzer may describe likely CAD operations, but it cannot:

- generate or execute CadQuery source;
- create, validate, or export a STEP file;
- invoke the future CAD MCP server;
- judge whether a rendered model matches the reference.

These restrictions prevent responsibilities and prompts from leaking across agents.

## Coordinate convention

The shared object frame is right-handed:

- `+X`: object width, toward image-right in the designated front view;
- `+Y`: object depth, from front toward rear;
- `+Z`: object height, upward.

The preferred origin is the base center. A later builder may change the origin only if it
records the transformation.

For a near-orthographic planar profile, the analyzer instead uses the image-aligned frame:
`+X` points image-right, `+Y` image-up, and `+Z` out of the profile plane. This makes local
silhouette ratios directly usable by the CAD builder.

## Scale policy

If the user supplies a reliable dimension, the analyzer uses the requested physical unit.
If no reliable scale exists, the prompt instructs Claude to use relative units and normalize
the largest overall dimension to `1.0`. Background objects are not treated as measuring
references unless the user explicitly identifies them.

## Future MCP boundary

The planned local CAD MCP server will consume the saved JSON specification. It will expose
high-level, restricted operations for CadQuery execution, STEP export, solid validation,
inspection, and preview rendering. The vision analyzer does not need MCP access because it
has no local CAD operation to perform.
