# Tasks

## 1. Scoped readable retention

- [x] 1.1 Implement semantic projection and digest-bound checkpoint storage; verify unit coverage for useful context, debris, tool pairing, bounds, expiry and isolation.
- [x] 1.2 Record successful settled native compactions and sweep retained checkpoints; verify native wire and failure invariants at the compact route.

## 2. Source recovery

- [x] 2.1 Materialize verified checkpoints before source inference and compaction, including continuation; verify HTTP and WebSocket switches, exact prefix handling and chained recovery.
- [x] 2.2 Sync specifications and document retention/recovery boundaries; verify spec validation.

## 3. Integration verification

- [x] 3.1 Run focused compaction, continuation and provider-history suites, lint, types and architecture checks; document results and any unrelated failures.
