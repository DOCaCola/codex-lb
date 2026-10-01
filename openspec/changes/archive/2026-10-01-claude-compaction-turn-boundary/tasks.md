# Tasks

## 1. Boundary

- [x] 1.1 Add a shared summarization instruction builder/splitter in source compaction; build requests with it.
- [x] 1.2 Replace the blanket complete-history rejection with the client-history boundary in `project_foreign_replay`; unify the active error wording.

## 2. Tests

- [x] 2.1 Unit: historical readable/opaque, closed final-assistant turn, interrupted turn, open tool loop refused, plaintext open loop allowed.
- [x] 2.2 Integration: HTTP compact endpoints and WebSocket trigger after a Sol-to-Opus switch succeed without ciphertext; open foreign loop refused without upstream call.

## 3. Verification and specification sync

- [x] 3.1 Run focused regressions, lint/types and spec validation; sync main spec/context.
