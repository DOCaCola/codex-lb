# Tasks

## 1. Credentials and enrollment

- [x] 1.1 Add typed Claude credential/import contracts and secure PKCE primitives; verify boundary and replay tests.
- [x] 1.2 Add encrypted account and enrollment persistence with single-head migration; verify isolated upgrade/downgrade and repository tests.
- [ ] 1.3 Implement generation-owned refresh classification, backoff and management enrollment; verify concurrent-worker, restart and redaction tests and document credential ownership.

## 2. Discovery and identity

- [ ] 2.1 Implement paginated catalog, selections and scoped quota monitoring; verify atomic-refresh and entitlement fixtures.
- [x] 2.2 Implement shared daily version following and pin/rollback; verify unchanged checks, stale feed and immutable snapshots.

## 3. Inference

- [ ] 3.1 Integrate eligible Claude pooling with source permissions, affinity and admission; verify two-account isolation and settlement tests.
- [ ] 3.2 Implement Messages/count-tokens forwarding with native errors, headers and SSE; verify fidelity, ping and cancellation route tests.
- [ ] 3.3 Implement Responses HTTP/WS adaptation, tools, multimodal and terminal semantics; verify roundtrip and pause/truncation fixtures.
- [ ] 3.4 Integrate durable continuation/compaction and ownership checks; verify restart, tool-result and model-switch tests.

## 4. Dashboard and integration

- [ ] 4.1 Integrate enrollment, account controls, model selection and quotas into shared UI; verify frontend tests and browser screenshots.
- [ ] 4.2 Document supported paths and live qualification limits; verify docs/spec alignment.
- [ ] 4.3 Run affected backend/frontend/type/lint/migration/OpenSpec checks and existing provider regression suites; record results without claiming live OAuth qualification.
