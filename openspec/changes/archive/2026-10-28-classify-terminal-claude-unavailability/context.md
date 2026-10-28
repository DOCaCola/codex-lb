# Investigation and validation

Observed 2026-10-28 against deployment 6daa4c4a60b4047f461561c07be92ab42f35ef70.
The service was healthy; previous-model compaction repeatedly received503
claude_pool_unavailable after the sole Claude grant became reauth_required.
The client's request_max_retries=15 delayed selected-model recovery by many minutes.

## Reference findings

Sources inspected 2026-10-28; no reference implementation copied.

- Codex 154e8736a51224e12b2d990753622a2cd8118f54,
  core/src/compact_model_fallback.rs and compact_remote_v2_installation.rs:
  existing selected-model fallback after the previous-model operation fails;
  installed 0.164.0-doca independently verified. This path is conditional on the
  provider/auth configuration; it is not a promise for every Responses client.
- OpenCodex 88aaa754566d119b6b8fc898f8fb47602387d82e,
  src/server/responses/compact.ts: merged PR2858 remembers a successful compact
  model on quota failure within an authenticated session lane. Its opt-in
  compaction-recovery-policy.ts emergency summary excludes authentication errors,
  budget errors, partial output and opaque native state. Neither fixes this retry
  classification problem or knows the newly selected client model.
- Sub2API b2e7c609430736bd0a4b89c5b27a079ccef820d4,
  backend/internal/service/openai_compact_fallback.go: bounded same-account model
  fallback for explicit compaction 400/404 model/context failures; no recovery of
  an expired Claude account.
- OmniRoute 8a8c64ee33b83803df74628a83f8372f7a1432c7,
  open-sse/services/contextHandoff.ts: bounded textual handoff, not native
  checkpoint preservation.
- Agent LB 77ba1fd9b26bf69e736b507cbd949aef842f498c,
  CLIProxyAPI ad8bdd3f20bef44f0684b8a6096a216b2c76040d and
  Frozen811 codex-lb 9d22321892602f2a762e166894bc63a7a74aa41b: no matching
  selected-model compaction recovery found in the inspected source.

## Independent evidence

- Isolated original-history replay, installed client, retries=15: old-model 400
  reaches Astra in 24 ms over HTTP and 128 ms over WebSocket. Both install a replayed
  native Astra checkpoint and complete a turn. No original chat was changed.
- Live Astra request b5f1a96d-4dc3-44c5-b2c6-3b3eab8b0c33: HTTP 200,
  completed in 100 seconds, 158409 input / 2304 output tokens, native compaction output.
- Native checkpoint continuation b4819054-145c-4853-9924-d5616d8c7e0d:
  HTTP 200, completed in 9 seconds, 2412 input / 197 output tokens. Four of five sampled
  history facts retained; normal summarization loss remains.
- No endpoint credentials, raw history or encrypted checkpoint is committed.
  Private reproduction artifacts remain outside this repository.

## Validation result

Focused routing/error/auth/ownership suites passed: the initial87-test set and the
expanded153-test Claude set. The shared-source/compaction/transport suites passed
300 tests initially; two new explicit-backend-compact cases lacked the required
instructions field. After correcting the fixture, all8 cases of that parametrized
test passed. No application workaround was needed.

make lint passed. ty check reported675 diagnostics both in an isolated unchanged
HEAD archive and the final working tree, with no new diagnostics after normalizing
line offsets. These existing failures still prevent a clean repository-wide type
gate. All77 main specs and the strict change validation passed before archival.
