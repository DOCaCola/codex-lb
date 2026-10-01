# Provider asset provenance

Inspected 2026-10-01. Marks identify account providers, not endorsements or model
vendors. Geometry is retained, wordmark paths are omitted and fills are black.
No remote image fetch happens in the user's dashboard.

- OpenAI: knot glyph extracted from the inline SVG served by https://openai.com/
  (41×41 viewBox, including on its JavaScript/cookie challenge page). Recolored
  from currentColor to black. Used for Codex accounts as explicitly requested;
  the application's own Codex branding remains unchanged.
- Claude: sunburst path extracted from the official https://claude.com/ header's
  Claude wordmark SVG (125×125 glyph, originally #D97757). Only the glyph remains.
- OpenRouter: official https://openrouter.ai/brand/v2/openrouter-glyph-light.svg,
  also present inline in https://openrouter.ai/. Purple replaced with black;
  the viewBox is trimmed to the same glyph bounds as the site's inline mark.

Shared marks are decorative, fixed at 16×16 and inverted in dark mode. Private
names remain separate spans. For example, an OpenRouter account serving GPT 6
Astra has an OpenRouter logo beside its account alias. The model ID remains in
the model label's native title even when a catalog/custom name is shown.

Historical requests may not appear in the current catalog. Their model IDs are
formatted into readable labels without changing persisted/filter identifiers.
Dashboard model-catalog loading never blocks the request-log surface. Existing
request detail/copy IDs and filter semantics are preserved.

## Verification

- 52 frontend test files / 639 tests passed, covering shared marks, readable
  models, account actions, privacy and existing dashboard behavior.
- Six browser cases passed at 320, 390 and 1440 pixels in light/dark mode after
  switching Codex accounts to the OpenAI knot. Actual local SVG loading, asset
  safety, native titles and all requested identity surfaces were checked.
  Updated desktop screenshot was visually inspected.
- Typecheck, changed-path ESLint and production frontend build passed.
- Strict change validation and all 75 main specs passed; spec/context synced.
- Verification used local fixtures, with no live provider requests.
