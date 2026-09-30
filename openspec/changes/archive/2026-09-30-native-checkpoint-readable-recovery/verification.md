# Verification

## Completeness and correctness

All five tasks implemented; specifications synced without archiving.

- Semantic projection preserves ordered messages, reasoning text, original
  instructions, direct tool pair IDs/results and attachments; it excludes known
  transport data, tool advertisements, local markers and ciphertext. Empty or
  unsupported history is not published as partial recovery.
- Successful settled native compact endpoints/Codex trigger bridging and full-input
  native WS completions publish scoped digest mappings. Native wire ciphertext
  and account routing remain unchanged. Failed compacts do not publish records.
- HTTP/WS source switches, source summarization, generic compatible sources and
  previous-response continuation restore visible context. Exact recorded compact
  prefixes are not duplicated; unrelated repeated turns remain intact.
- Chained records, restart, TTL, eviction, byte limits, corrupt files, cross-scope
  lookups and original-index rejection are covered by unit/regression tests.

The broad compaction/continuation/provider-history suite passed 389 tests; the two
subsequently added generic-source and native-refusal cases also passed. Latest
new-feature-only run: 36 tests passed. Modified application files pass Ruff format,
Ruff checks and targeted ty checks. Strict change/spec validation passes. Timing
seams and migration topology checks pass.

## Existing baseline failures

Confirmed against an unchanged git archive of HEAD f6e33cd81 (not inferred):

- Two utility cases of transparent_replay_strips_socket_turn_state_on_reattach
  fail with missing model_sources table in their unit-test database. They fail
  identically without this change; the additional broad replay slice stopped
  after these failures (86 preceding tests passed).
- Full application ty reports six reasoning-policy type mismatches in accounts
  service, Claude routing and OpenRouter catalog/routing. No new diagnostics in
  the modified application files.
- Architecture ratchets already fail: service.py 2603/2600 lines,
  load_balancer.py 3038/3021, http_bridge/mixin.py 2472/2436. Those files are
  unchanged by this work.

## Coherence and boundaries

The shared replay storage moved out of the WebSocket package because eager mixin
imports create a circular dependency when native compaction imports storage.
All consumers now import the shared module; no compatibility shim was added.
The new namespace has the existing one-hour bounded private retention policy.

Source recovery does not decode private native state or synthesize missing
history. Legacy/unobserved checkpoints, native handle-only compaction and hosted
resource state remain unsupported. Generic native V1 generation streams keep
their existing behavior; native V1 capture uses the dedicated compact endpoint.
Provider-capacity errors are not retried with shortened history.

Mock/provider stub qualification only. Production, client files, credentials,
upstream accounts and live conversations were not modified. No commit, push,
deployment or archive performed.
