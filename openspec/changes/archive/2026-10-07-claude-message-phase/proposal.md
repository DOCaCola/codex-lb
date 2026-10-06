# Claude Message Phase

## Why

Translated Claude responses deliver assistant messages without a Responses `phase`. Codex uses the phase:

- Forked threads keep only assistant messages whose phase is `final_answer` (`keep_forked_rollout_item`), so a child
  forked from a Claude parent loses every answer the parent gave.
- A `commentary` message marks work still in progress, which allows mailbox preemption between tool calls.

Claude marks no phase, but its stop reason shows what a message was: text followed by a tool call or ended by
`tool_use` is commentary; text ended by `end_turn` or `stop_sequence` is the answer. opencodex infers the phase the
same way when it closes the message (`d2cc3f65e`).

## What Changes

- The translated message stays open after its text block stops. The next valid content block closes it as
  `commentary`; the stop reason closes it as `final_answer` (`end_turn`, `stop_sequence`) or `commentary`
  (`tool_use`). Truncated, paused and refused stops, and streams that fail, close it without a phase.
- Consecutive text blocks form one message with one `output_text` part per block, so a single message is open at a
  time.
- A stream that fails after a finished text block still closes that message before its error, so the client keeps
  output it already received.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: adds "Translated assistant messages carry a Responses phase".

## Impact

- `app/modules/claude/responses.py` (`ResponsesProjection`), `app/modules/claude/transport.py` (failure path).
- Applies to streamed and non-streamed translated Responses and Chat, which share the projection.
- Native passthrough is unchanged.
