# Tasks

## 1. Projection and authentication

- [x] 1.1 Implement immutable provider-aware projection and indexed authentication errors; verify unit coverage for plaintext, encrypted historical/active/opaque-only items, genuine empty signed blocks, tampering and fork scopes.
- [x] 1.2 Apply the boundary before Claude account selection; verify public HTTP/WebSocket and retained replay preserve summaries and tools without mutating logical history.
- [x] 1.3 Verify complete compaction rejects unavailable foreign state and preserves plaintext-only history through route tests; record reference rationale and sync specs during archive.

## 2. Release verification

- [x] 2.1 Run focused Claude/native-history regression suites, format/lint/type checks and strict spec validation; review the diff before archive.

## Delivery after archive

Commit under DOCa Cola, integrate into main and push. Deploy through the existing
production upgrade.sh and verify image revision/readiness without modifying live
conversation history. These delivery actions follow verified implementation and
are not claimed complete by archiving the change.
