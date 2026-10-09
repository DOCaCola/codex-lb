# Verification (2026-09-30)

## Completeness and correctness

All six implementation tasks completed; the added requirement and all six
scenarios are covered. Main Claude account spec/context are synced. No schema,
provider enrollment, routing settings or production changes were made.

- `app/modules/claude/replay.py`: authenticates before converting readable
  thinking; precise invalid/nonportable-history errors; unchanged logical items.
- `app/modules/proxy/native_history.py`: uses existing API-key/client conversation
  identity; lazy cryptographic decoding only for Claude envelopes; separate wire
  request copy.
- Native raw HTTP and HTTP bridge entry, WebSocket preparation and compaction:
  shared projection before dispatch; retained WebSocket expansion precedes
  conversion and saves original replay input. Source-owned requests retain their
  provider policy. Native synthesized handshake state does not become source
  envelope authentication scope.
- `app/core/openai/reasoning.py`: preserves distinct plaintext and summary text;
  rejects unrepresentable content instead of emptying it silently; validates
  known ID prefixes without changing call IDs; preserves native opaque state.
- Native transport and fresh-frame serialization reject unprojected envelopes.

## Checks

- New unit/integration regressions: **27 passed**, including public keyed
  WebSocket send/receive, HTTP aliases, compaction, retained continuation, bridge
  preparation, scope/tampering checks and explicit redacted/search refusal.
- Focused native/reasoning/preparation run: **131 passed**.
- Compaction/Claude replay/protocol/inference/affinity regressions: **228 passed**.
- Model-source guards, WebSocket client and stream timeout tests: **98 passed**.
- Ruff check and format check, scoped ty check and git diff whitespace: passed.
- Strict change validation: passed. Strict main-spec validation: **73 passed,
  zero failed**; existing informational long-requirement notices remain.

The initial broad proxy/transport/HTTP bridge/contract run passed 2566 tests and
failed 22 existing direct-WebSocket tests. Their failures originate in the
unmocked source-dispatch database path (`no such table: model_sources`), before
native projection. The same 22 failures reproduce from an untouched archive of
baseline `a1cab7b4440e18e19786a2f97f7a88514f941b67`; that temporary checkout also
has one additional HTTP bridge source-inspection failure. These unrelated
harness problems were not changed as part of provider-history conversion.

## Qualification limits

Synthetic upstreams verify complete client-facing dispatch and rejection paths,
not current live OpenAI acceptance of a particular conversation, OAuth eligibility
or billing. No real provider requests or production deployment were performed.
The intentional nonportable-state error is not a claim that redacted or hosted
resource data can be reconstructed on OpenAI. Original data remains available
in the retained Claude history.
