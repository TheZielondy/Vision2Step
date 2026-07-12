# Roadmap

## Milestone 1 — Vision analyzer

- [x] Validate and encode reference images
- [x] Analyze multiple views in one request
- [x] Enforce a builder-ready structured contract
- [x] Persist raw deterministic geometry hints
- [x] Record provenance and token usage
- [x] Provide a CLI and offline tests

## Milestone 2 — CadQuery builder

- [x] Use an independent Builder Claude context
- [x] Convert the specification into editable CadQuery source
- [x] Keep `model.py` as the parametric source of truth
- [x] Apply deterministic evidence-priority guidance
- [x] Record assumptions, contradictions, and omitted features
- [x] Export and reopen a BREP-based STEP artifact
- [ ] Automatically ask Builder Claude to repair execution failures

## Milestone 3 — Local CAD MCP server

- [x] Execute generated CAD in immutable candidate directories
- [x] Apply AST restrictions, a sanitized environment, and a subprocess timeout
- [x] Validate solids and reopen exported STEP files
- [x] Expose build, validation, inspection, and artifact-listing tools
- [ ] Render standardized comparison views

## Milestone 4 — Grading and iteration

- [ ] Add reference-aligned, top, front, side, and isometric renders
- [ ] Implement deterministic validation on every run
- [ ] Implement `loop`, `final`, and `off` Claude-grader policies
- [ ] Distinguish grader acceptance from bypassed completion
- [ ] Stop on score threshold, stalled improvement, or iteration limit
