# Tasks

## 1. Signed history

- [x] 1.1 Use the shared client-history boundary in `authenticate_replay`; drop compaction-wide strictness and its errors.
- [x] 1.2 Project mismatched completed thinking as readable text for compaction; omit otherwise; count-only diagnostics.
- [x] 1.3 Compaction signature recovery converts historical thinking to text; remove the transport skip.

## 2. Unsigned open tool turn

- [x] 2.1 Detect an open tool-use turn without leading signed thinking after projection; send disabled thinking in budget mode.

## 3. Tests

- [x] 3.1 Unit: replay strictness/projection, recovery modes, protocol open-turn detection (budget/adaptive, continue tail, signed loop).
- [x] 3.2 Integration: compact endpoints after model switch, paused owner and signature rejection; WebSocket compaction; unsigned budget tool loop.

## 4. Verification and specification sync

- [x] 4.1 Run focused regressions, lint/types and spec validation; sync main specs and context.
