# Vision2STEP

Vision2STEP is an image-to-CAD workflow that will turn reference images into validated
STEP models through specialized Claude agents and deterministic CAD tools.

**Current milestone:** the vision analyzer is implemented. It converts one or more
reference images into a validated, CAD-oriented JSON specification. CAD construction,
MCP tools, STEP export, and grading are intentionally reserved for later milestones.

## Why this project exists

A single image is not a 3D model: scale, depth, and hidden surfaces are ambiguous.
Vision2STEP makes those uncertainties explicit before any geometry is created. Every
geometric claim is classified as `observed`, `inferred`, or `unknown`, giving the future
builder a more reliable input than an unconstrained prose description.

```mermaid
flowchart LR
    A[Reference images] --> B[Claude vision analyzer]
    B --> C[Validated CAD specification]
    C -. future .-> D[CadQuery builder]
    D -. future .-> E[STEP model]
```

## Implemented features

- JPEG, PNG, GIF, and WebP input validation
- Single-view and multi-view analysis
- Token-free local measurement of foreground bounds, aspect ratio, and enclosed holes
- SHA-256 image provenance without exposing absolute local paths
- Claude structured outputs backed by Pydantic models
- Lean schema v1.2 designed to stay within Claude's grammar-compilation limits
- CAD-oriented decomposition into components, features, relations, and build steps
- Camera-pose and bounded-dimension estimates
- Explicit assumptions, unknowns, and clarification questions
- Token usage recorded in every output artifact
- CLI suitable for scripts and future orchestration
- Unit tests that make no live API calls

The analyzer uses Claude's documented [vision input](https://platform.claude.com/docs/en/build-with-claude/vision)
and [structured output](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
features.

## Installation

Python 3.11 or newer is required.

```bash
git clone https://github.com/your-username/vision2step.git
cd vision2step
python -m venv .venv
```

Activate the virtual environment, then install the project:

```bash
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and provide your Anthropic API key:

```env
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-6
VISION2STEP_MAX_TOKENS=3500
```

## Analyze an object

Analyze one image:

```bash
vision2step analyze reference.png --context "The overall width is 120 mm"
```

Analyze several labeled views together:

```bash
vision2step analyze front.png side.png top.png \
  --unit mm \
  --output artifacts/bracket-analysis.json
```

Use a lower-cost model when desired:

```bash
vision2step analyze reference.png --model claude-haiku-4-5-20251001
```

The default output path is `artifacts/<image-name>-analysis.json`.

## Output contract

Each artifact contains:

```text
artifact metadata
├── model and Claude response ID
├── source image names, sizes, types, and hashes
├── input and output token usage
└── specification
    ├── coordinate system, camera estimate, and modeling class
    ├── overall dimensions and evidence
    ├── components and local features
    ├── assumptions, unknowns, and questions
    ├── ordered CAD build strategy
    └── future grading anchors
```

The authoritative contract is defined in
[`src/vision2step/models.py`](src/vision2step/models.py). An illustrative, manually
authored contract example is provided under [`examples/`](examples/); it is not presented
as a real Claude run.

## Test the analyzer

The standard-library test suite can run before optional development tools are installed:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

After installing development dependencies:

```bash
ruff check .
pytest
```

## Current limitations

- No STEP file is generated in this milestone.
- Absolute scale requires a supplied measurement or trustworthy scale reference.
- Hidden geometry remains inferred or unknown.
- Claude's spatial measurements are approximate and require later geometric validation.
- Transparent, reflective, deformable, and highly organic objects are poor initial targets.

## License

MIT
