# Tasks

## 1. Recovery core

- [x] 1.1 Identities, digest store (24 h retention refreshed on hit, 20,000-entry LRU), payload and serialized-body helpers with an explicit request operation; checkpoint handoff excluded.
- [x] 1.2 Strip remembered ciphertext at the start of `sanitize_native_responses_input`.
- [x] 1.3 Single retry in `stream_responses` (refusal before any response event) and `compact_responses`.

## 2. WebSocket and HTTP bridge

- [x] 2.1 Classify the refusal on pre-created and accepted output-free terminals.
- [x] 2.2 Remember on every explicit refusal; replay once on the direct WebSocket (anchored requests as the stripped full-history body) and on the bridge, without health write or exclusion.
- [x] 2.3 Keep the bridge retry on its account (`rejected_encrypted_content_replay`).
- [x] 2.4 Payload-rejection health rule uses the same identities.

## 3. Verification

- [x] 3.1 Unit tests for identities, removal per carrier, retention, eviction, handoff exclusion, text helpers and the sanitizer.
- [x] 3.2 HTTP stream and compaction retry tests, including a refusal of a body without ciphertext.
- [x] 3.3 WebSocket accepted, pre-created, anchored and second-refusal tests; bridge accepted test (same account, no health write).
- [x] 3.4 ruff, ty, proxy architecture check, strict OpenSpec validation, regression suites.
