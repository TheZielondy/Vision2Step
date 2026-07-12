# Changelog

## 0.2.7 - 2026-07-12

- Changed the normal `build` and token-free `execute-source` commands to call the isolated CAD
  execution service directly instead of spawning it from inside the MCP server.
- Eliminated the Windows-only double-subprocess startup failure while retaining API-key removal,
  `-I` isolation, timeouts, source policy checks, STEP re-import, and single-solid validation.
- Kept the FastMCP server as an optional integration interface rather than a dependency of the
  normal command-line workflow.
- Updated workflow tests and architecture documentation for direct CLI execution.

## 0.2.6 - 2026-07-11

- Fixed Windows CAD subprocess startup by preserving normal OS and virtual-environment variables
  while explicitly removing API keys, tokens, credentials, and Python injection variables.
- Applied the same environment policy to both the MCP server process and isolated CAD runner.
- Added a parent-side `runner_process_starting` diagnostic that distinguishes startup failures
  from pathological generated geometry.
- Added `execute-source` to validate and rebuild a retained `model.py` through the normal MCP and
  isolated-runner path without a Claude API call.
- Added Windows environment, startup-timeout, and token-free CLI regression tests.
- Constrained supported Python versions to 3.11-3.12 and documented an explicit Python 3.12
  virtual-environment command for Windows.
- Forced UTF-8 decoding with replacement for CAD runner output on Windows.

## 0.2.5 - 2026-07-11

- Rejected solid boolean operations on unextruded 2D profiles before CadQuery execution.
- Clarified the planar builder contract: use one Workplane with pending wires and one extrusion,
  or extrude separate components before performing solid booleans.
- Added regression coverage for the cutting-board timeout pattern and valid solid booleans.
- Added explicit radius-arc feasibility and duplicate-endpoint guidance for generated profiles.
- Required both the generated candidate and reopened STEP to contain exactly one valid solid.
- Clarified continuous-silhouette construction for integrated handles and other extensions.
- Reduced the default Builder Claude output ceiling from 4,000 to 3,000 tokens.

## 0.2.4 - 2026-07-11

- Added statement-level source execution stages with exact `model.py` line ranges.
- Added `last-stage.txt` as a Windows-safe timeout diagnostic fallback.
- Reworded timeout errors to distinguish pathological geometry from cold starts.
- Constrained planar-extrusion proposals to compact Workplane profiles and one extrusion, avoiding Sketch solving and expensive finishing operations.

## 0.2.3 - 2026-07-11

- Increased the default CadQuery execution timeout from 30 to 120 seconds to accommodate Windows cold starts and STEP import/export overhead.
- Added runner stage reporting so timeout errors identify the operation that was active.
- Failed candidate directories are archived under `artifacts/candidates/_failed/` on retry, allowing the same candidate ID to be reused while preserving diagnostics.

## 0.2.1 — 2026-07-11

- Allowed the documented CadQuery `radiusArc` method in restricted builder source.
- Removed staged full-build proposals after validation or execution failure so the candidate ID can
  be retried.
- Clarified symmetric `extrude(..., both=True)` thickness semantics in the builder prompt.
- Added a source-policy regression test for rounded profiles built with `radiusArc`.

## 0.2.0 — 2026-07-11

- Persisted deterministic geometry hints in analyzer artifact version 1.3.
- Added an independent Builder Claude with compact proposal schema 1.0.
- Added evidence-priority, contradiction, assumption, and omission reporting.
- Added a restricted linear CadQuery AST policy.
- Added immutable candidate workspaces and sanitized subprocess execution.
- Added STEP export, fresh re-import validation, dimensions, area, volume, and solid count.
- Added a local FastMCP server and stdio client with four CAD tools.
- Added the `vision2step build` workflow and proposal-only mode.
- Added token-free `vision2step enrich` migration for existing v1.2 analysis reports.
- Added real CadQuery and end-to-end MCP runtime smoke verification.
- Expanded the offline suite from eight to eighteen tests.

## 0.1.2 — 2026-07-11

- Added a local Pillow-based foreground and enclosed-hole measurement pass.
- Added normalized silhouette evidence to the Claude request without another API call.
- Added planar-extrusion classification and image-aligned coordinate guidance.
- Prevented low-confidence inferred features from entering the default build strategy.
- Reduced the default output limit from 6,000 to 3,500 tokens.
- Removed appearance, function, image-assessment, and duplicated relation fields from the
  output contract and bumped it to v1.2.
- Added synthetic silhouette and oval-hole tests.

## 0.1.1 — 2026-07-11

- Reduced the Claude output schema from thirteen nested definitions to two.
- Replaced deeply nested dimension, camera, relation, and build-step records with documented
  canonical strings while retaining structured components and features.
- Bumped the artifact and specification contracts to v1.1.
- Added a regression test that caps the generated Claude schema size.
- Documented recovery from Claude's `compiled grammar is too large` API error.

## 0.1.0 — 2026-07-11

- Implemented the initial vision analyzer milestone.
