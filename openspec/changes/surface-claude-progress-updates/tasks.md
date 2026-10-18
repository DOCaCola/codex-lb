# Tasks

## 1. Implementation

- [x] 1.1 Add the progress-display model set to `capabilities.py` with its CLIProxyAPI source.
- [x] 1.2 Project `thinking.display: "updates"` in `protocol.py` when the model is in the set, thinking is adaptive or
  enabled and the caller chose no display; negotiate `thinking-display-updates-2026-08-18` in `dispatch.py`.
- [x] 1.3 Buffer non-empty signed thinking under `updates` in `responses.py`; at block stop emit the empty-summary
  carrier with presented opaque state and a separate done commentary message.
- [x] 1.4 Add `presented` to `SignedBlock` in `opaque.py`.
- [x] 1.5 Consume the adjacent exact commentary copy when forwarding a presented block in `replay.py`.
- [x] 1.6 Skip readable conversion of a presented block whose copy is present in `replay.py`.
- [x] 1.7 Add `progress_updates` to the translated stop diagnostic.
- [x] 1.8 Record the rationale and an example in `openspec/specs/claude-accounts/context.md`.

## 2. Verification

- [x] 2.1 Request projection: display and beta set for each model in the set; absent for Haiku 5.5, disabled thinking,
  explicit `summarized`/`omitted` and native Messages.
- [x] 2.2 Stream: an update before a tool call yields carrier, commentary copy and call in order over SSE and JSON; an
  empty block stays a plain reasoning item; a failure inside the block emits neither; an interrupted-stop update keeps
  the incomplete status.
- [x] 2.3 Replay: exact copy consumed with and without message IDs; edited copy kept; missing copy tolerated; legacy
  envelopes without the marker unchanged; block order before `tool_use` preserved.
- [x] 2.4 Projections: compaction and OpenAI handoff contain the update text exactly once.
