## Why
Production Claude turns failed as `invalid_upstream_response` ("Claude stopped before closing its content and stop reason") a few output tokens into the stream. Anthropic documents that a refusal can arrive mid-stream while a content block, including a tool call, is still open. The adapter treated every open block at `message_stop` as a protocol violation, so a documented refusal became an opaque gateway error instead of Codex's content-filter path. `pause_turn` reached Chat clients as an unknown incomplete reason, `model_context_window_exceeded` was rejected as unknown, failing stops left no stop diagnostics, and transport drops did not name their cause.

## What Changes
- A translated refusal stop is valid with open content blocks or pending search calls. It ends as incomplete with reason `content_filter`; the partial output is discarded, as Anthropic advises: it never receives done events and is left out of the terminal output and continuation history, so no unfinished tool call reaches the client as executable or is replayed without a result.
- Native passthrough forwards a refusal with open blocks unchanged and records refusal and `model_context_window_exceeded` as incomplete terminals.
- `pause_turn` and `model_context_window_exceeded` map to incomplete reason `max_output_tokens`, as in opencodex.
- Any other unfinished stop remains an error whose message names open block types, pending search count and stop reason; the stop diagnostic log line is written before failing.
- Transport failures name the exception class.

## Capabilities
### Modified Capabilities
- `claude-accounts`: Claude stream terminal semantics.

## Impact
Claude Responses projection, native observer and transport error messages. No schema or configuration changes.
