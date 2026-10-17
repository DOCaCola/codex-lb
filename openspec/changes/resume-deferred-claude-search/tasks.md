# Tasks

## 1. Implementation

- [x] 1.1 Accept call-only search state in `search.py` replay validation.
- [x] 1.2 Defer pending searches on a `tool_use` stop with a client tool call in `responses.py`; accept the result of a
  resumable deferred call and store it as a pair for the original item.
- [x] 1.3 Restore deferred calls ahead of their turn's client tool calls in `protocol.py`; forward resumable calls,
  omit and log the rest, and expose resumable calls on the projection.
- [x] 1.4 Treat deferred state in account replay and OpenAI handoff projections (`replay.py`).

## 2. Verification

- [x] 2.1 Stream tests: deferral beside a client tool, pending search without a client tool still fails, resumed
  result stored as a pair, unknown result fails.
- [x] 2.2 Protocol tests: resumable call forwarded in order with the result pair later in history; omission for
  interrupted, extra-content and search-undeclared turns.
- [x] 2.3 Replay tests: foreign-account and OpenAI projections of answered and unanswered deferred searches.
