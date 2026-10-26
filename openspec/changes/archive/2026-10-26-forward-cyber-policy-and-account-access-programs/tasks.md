# Tasks

## 1. Refusal handling

- [x] 1.1 Detect security-work refusals by exact code (`cyber_policy`, `security_work_authorization_required`) in one
  shared helper; remove message-hint matching and the compaction copy.
- [x] 1.2 Keep the upstream code of the refusal on HTTP streaming, WebSocket and in request logs.
- [x] 1.3 Forward the original refusal when no authorized account exists over HTTP streaming and compaction instead of
  continuing normal account failover; update the advisory wording.

## 2. Per-account access programs

- [x] 2.1 Record per-model cyber programs per account in the model registry and its persisted snapshot.
- [x] 2.2 Resolve the program for an account and model; stamp it with the installation id through one account stamp.
- [x] 2.3 Apply the stamp on HTTP streaming, compaction (including warmup and automations), the HTTP bridge and
  WebSocket; strip it from bridge fingerprints; treat the field as account-neutral for replay.

## 3. Verification

- [x] 3.1 Unit tests for detection, forwarding without normal failover, code preservation, registry lookup, snapshot
  codec and stamping.
- [x] 3.2 Full test suite, ruff, ty and `openspec validate --specs`.
