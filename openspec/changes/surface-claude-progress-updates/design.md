# Design: Surface Claude Progress Updates

## Context

Anthropic's thinking documentation ("Progress updates between tool calls", "Controlling thinking display") defines
three display values for the 5.x models:

| display | reasoning blocks | progress-update blocks |
| --- | --- | --- |
| `omitted` (default) | empty `thinking` | empty `thinking` |
| `summarized` | summary text | summary text, indistinguishable from reasoning |
| `updates` (beta) | empty `thinking` | summary text |

Under `updates`, any `thinking` block with non-empty text is a progress update. Each update is its own signed block
placed immediately before the `tool_use` or `server_tool_use` it introduces. Signed blocks must be returned unchanged
and in order; text placed in an empty block's `thinking` field is ignored.

## Decisions

### Request shape follows Claude Code

The models are Claude Code's progress-display set as CLIProxyAPI measured it: `claude-opus-5-5`, `claude-fable-5-1`
(and `claude-mythos-5-1`), `claude-sonnet-5`, `claude-sonnet-5-5`, with dated aliases. Haiku 5.5 is excluded.
The display is set only when thinking is `adaptive` or `enabled`; Anthropic rejects `display` with `disabled`.
A caller's explicit Responses `reasoning.display` (`summarized` or `omitted`) wins. Chat Completions always projects
an explicit display (`summarized` by default), so the rule never applies there. The beta is added in `dispatch.py`
with the other feature betas whenever the projected body carries `updates`, whatever its route.

### Presentation is atomic per block

The block's text streams as `thinking_delta` before its `signature_delta`. The carrier's `output_item.added` (an
empty reasoning item) is sent when the block opens, as for any thinking block; its text is buffered. At
`content_block_stop` the translator emits the carrier's done event (empty summary, opaque state) and then a separate
commentary message (`output_item.added`, `output_text.delta`, `output_text.done`, `output_item.done`) at the next
output index; later blocks shift by one. A stream that fails inside the block emits neither the copy nor the carrier's
done event, so the client never holds a visible copy without its replay carrier. Updates are a sentence or two and
Anthropic documents the pause before the block opens, so buffering adds no noticeable delay.

An open text message is closed with phase `commentary` by the thinking block, as today. The copy never joins another
message. When a response stops on `max_tokens`, `model_context_window_exceeded` or `stop_sequence`, Anthropic may
end with an update reading "This part of the response was interrupted before it finished."; it is shown like any
other update and the response keeps its incomplete status.

Chat Completions keeps today's reasoning-summary behavior: it asks for `summarized` explicitly, so no update is
presented there.

### Replay pairs by adjacency and exact text

`SignedBlock` gains `presented: bool = False`. When replay (`ClaudeReplay.project`) forwards a presented block, the next input item
is checked: an assistant message with phase `commentary` or no phase, whose concatenated text equals the block's
`thinking` exactly, is consumed. Message IDs are not required because clients may omit them (opencodex replays the
same way). Anything else, including an edited copy, is replayed as ordinary assistant text after the restored block,
exactly as the client sent it. The restored block keeps its original position before its `tool_use`.

### Readable projections avoid duplicates

When compaction or a handoff converts completed thinking into readable text, a presented block whose adjacent copy is
present converts to nothing; the copy already carries the text and is portable to any provider. A presented block
without its copy converts to readable text, as today. OpenAI dispatch, which drops Claude opaque state, keeps the copy,
so progress updates become portable context after a model switch.

### Diagnostics

The existing translated stop log line gains `progress_updates=<count>`. No content is logged.

## Risks

- **OAuth acceptance of the beta** is not established by our own traffic. Claude Code sends it over OAuth for these
  models (CLIProxyAPI capture) and opencodex sends it for OAuth Opus 5.5. A rejection is a 400 on every request for
  the affected model, visible immediately after deploy; it is not retried silently.
- **Fewer updates at higher effort.** Anthropic notes that these models write fewer updates at higher effort and in
  long tool chains, so a steer can still go unanswered in visible text. This change does not prompt for updates.
- **Delivery latency is unchanged.** Claude catalog entries are not Responses Lite, so Codex still delivers a steer at
  the next tool boundary rather than interrupting the running response.

## Non-goals

- Prompting the model to write more updates.
- `response.steer` for Claude; CLIProxyAPI and opencodex restrict it to native ChatGPT routes.
- Changes to native Messages forwarding.
