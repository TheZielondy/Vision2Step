# Changelog

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
