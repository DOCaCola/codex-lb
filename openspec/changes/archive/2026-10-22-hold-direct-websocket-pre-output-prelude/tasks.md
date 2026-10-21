# Tasks

## 1. Implementation

- [x] 1.1 Hold the lifecycle and metadata prelude of a sole, replayable, model-generating direct WebSocket request for
  at most 10 seconds (`_websocket_prelude_hold_accepts`, `_hold_websocket_prelude_text`).
- [x] 1.2 Commit held frames before the response's next forwarded frame and before another request's frame; set the
  sequence watermark from the sent frames.
- [x] 1.3 Wake the relay at the hold deadline and commit expired holds (`_commit_expired_websocket_prelude_holds`).
- [x] 1.4 Keep held frames across the accepted replay; check replay sequences against the held watermark and exempt the
  replay's suppressed `response.in_progress`.
- [x] 1.5 Keepalives treat a holding request as pre-created; synthesized terminal failures send held frames first, and only a capability-lineage persistence failure discards them.
- [x] 1.6 Stop counting `response.queued` and `response.metadata` as lifecycle events.

## 2. Verification

- [x] 2.1 Integration tests: held sequenced overload and abrupt close replay within one lifecycle with advancing
  sequences; after the hold they fail closed; silence past the deadline commits the prelude; a replay that does not
  advance beyond the held prelude closes with 1011.
- [x] 2.2 Unit tests: hold predicate, deadline, metadata counting, keepalive during a hold, deadline commit.
- [x] 2.3 ruff, ty, pytest, strict OpenSpec validation.

