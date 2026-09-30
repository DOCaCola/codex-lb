# Tasks

## 1. Provenance and bounded handoff

- [x] 1.1 Record provenance without native input retention; test scope isolation, older opaque input, failed native compaction and byte bounds.
- [x] 1.2 Implement summary-cache and generation claims; test restart reuse, concurrency, expiry and cleanup on failure/cancellation.

## 2. Native generation and source integration

- [x] 2.1 Add hard-owner native handoff through existing settlement lifecycle; test unavailable/restricted owners, no account failover and usage logs.
- [x] 2.2 Integrate HTTP/WS inference, continuation and source compaction; test unchanged readable/native requests, cached replay, invalid summaries and history ordering.

## 3. Verification and specification sync

- [x] 3.1 Sync main specs/context and run focused regression, lint/types, timing and spec gates; record live-qualification limitations and unrelated failures.
