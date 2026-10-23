# Tasks

## 1. Implementation

- [x] 1.1 Record the materialized input of every direct WebSocket request whose full context is known, and the output
  of its completed or interrupted response, computed once at the terminal.
- [x] 1.2 Record the last completed response's history and the last empty prewarm's history on the continuity state;
  clear them with their anchor.
- [x] 1.3 Expand a client delta anchored to a recorded response into a retry-safe fresh payload.
- [x] 1.4 Send the next turn anchored to a replayed response's visible id as the recorded conversation plus its delta.
- [x] 1.5 Replay anchored requests with their fresh payload, keeping the owner pin when the payload cannot move.
- [x] 1.6 Raise the pre-output hold to 40 seconds.
- [x] 1.7 Log refused replays of replayable terminals with their reason.

## 2. Verification

- [x] 2.1 Integration tests: a Codex delta follow-up overloaded after acceptance is replayed with its history, and the
  next turn anchored to the visible id is sent in full; a turn chained to an empty prewarm is replayed with the prewarm
  context; a client-anchored owner replay sends the fresh body; a recorded delta whose anchor upstream lost is
  recovered with its history instead of failing.
- [x] 2.1a Masking tests that read a pipelined request's `response.created` disable the pre-output hold, which they do
  not exercise.
- [x] 2.2 Unit tests: owner-bound anchored replay bodies and refusal reasons with their log line.
- [x] 2.3 ruff, ty, pytest, strict OpenSpec validation.
