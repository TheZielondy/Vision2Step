# Roadmap

## Milestone 1 — Vision analyzer

- [x] Validate and encode reference images
- [x] Analyze multiple views in one request
- [x] Enforce a builder-ready structured contract
- [x] Record provenance and token usage
- [x] Provide a CLI and offline unit tests

## Milestone 2 — CadQuery builder

- [ ] Convert the specification into editable CadQuery source
- [ ] Keep `model.py` as the parametric source of truth
- [ ] Export a BREP-based STEP artifact
- [ ] Return repairable construction errors

## Milestone 3 — Local CAD MCP server

- [ ] Execute generated CAD in an isolated working directory
- [ ] Apply time, import, and output limits
- [ ] Validate solids and reopen exported STEP files
- [ ] Render standardized comparison views

## Milestone 4 — Grading and iteration

- [ ] Implement deterministic validation on every run
- [ ] Implement `loop`, `final`, and `off` Claude-grader policies
- [ ] Distinguish grader acceptance from bypassed completion
- [ ] Stop on score threshold, stalled improvement, or iteration limit

