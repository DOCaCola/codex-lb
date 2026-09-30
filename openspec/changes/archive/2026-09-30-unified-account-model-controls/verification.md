# Verification

## Completeness and correctness

The change implements all four provider/account requirements and the shared
chart requirements. API and UI tests cover defaults, retained curated choices,
automatic provider projection, native discovery filtering, invalid selections,
read-only permissions, failed saves, migration roundtrip and routing priority.
The public WebSocket regression confirms retirement after an operator restriction;
HTTP bridge compatibility reads updated policy even from a stale account object.
Strict-owner routing remains fail-closed. Native image generation/editing tests
exercise both All and empty selected modes without changing image entitlement.

Routing snapshot tests also cover a repeated identical local policy write during
an in-flight refresh: update identity, not value equality, preserves that write.
A subsequent database snapshot replaces older overlays, including another
replica's change.

## Evidence

- 223 account/Claude/OpenRouter frontend component tests passed.
- Broad backend routing/transport/provider suite: 1457 passed, one existing
  cross-provider-history assertion failed (see baseline findings below).
- Native controls, permission matrix and permission gates: 30 passed, including
  the added model-policy refresh race.
- Image routes and account controls: 110 passed, including native generation and
  editing in both conversation-model modes.
- TypeScript, production frontend build, targeted ESLint, `make lint` (including
  migration topology and architecture ratchets), and strict OpenSpec validation
  passed. Migration upgrade/downgrade and schema-drift tests passed.
- Two real-browser tests cover desktop/mobile pages and dialogs for all three
  providers, horizontal overflow, saved-selection retention and real chart SVG
  paths. Native/provider curves contain no NaN coordinates. Claude measured
  curves have exactly two segments around an explicitly missing hour; a mid-hour
  guideline creates no extra segment. Screenshots were visually inspected.

The read-only production chart investigation found 29 known five-hour/weekly
observations among 168 hourly samples, and three extra axis timestamps from a
171-point weekly-plan series. The previous merged-data renderer injected nulls
at those guideline-only timestamps. Independent series data fixes that root
cause without inventing observations or resetting history.

## Baseline findings outside this change

Baseline revision: `dd06c84f8`. The same failures were reproduced in a clean
temporary worktree, which was removed after comparison:

- `test_backend_responses_websocket_sanitizes_source_reasoning_for_native_upstream`
  expects an empty reasoning item without the summary preserved by preceding
  commit `57f8706dc`. This change does not remove that preservation.
- Korean and simplified-Chinese locale-key parity each miss existing routing
  keys. No locale files were changed by this feature.
- MSW handler inventory omits the pre-existing two provider-trend and two quota
  webhook reads. This feature registers its two new native model endpoints in
  both handlers and expected inventory; the remaining mismatch is identical to
  baseline.

The full frontend run reported 1756 passed and those three baseline failures;
the final feature-specific frontend run is fully green.

## Coherence and operational state

Provider details reuse native surfaces, quota, routing, model-mode and dialog
components. Provider-specific monitoring retains its own units and unknown
states. Claude capacity/version controls remain available in Provider settings.
Main specifications and user docs are synchronized. No existing token limits,
continuation ownership, production configuration or image-backend choice changed.

No commit, push, archive or deployment was performed. Live provider acceptance is
not established by local mocks; production was inspected read-only.
