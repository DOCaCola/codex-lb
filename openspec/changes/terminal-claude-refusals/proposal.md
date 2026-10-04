# Proposal

## Why

A translated Claude refusal surfaced as `incomplete` with reason `content_filter`. Codex treats that as a sampling filter: it adds `<content_filter_guidance>` and retries. Claude's refusal is the safety classifier declining the request, and Anthropic documents that the same model usually declines it again. Production thread `01a100b5` retried ten times, each refusing again and each paying roughly 26k cache-write tokens at the 1h rate. Every retry also replayed the refused attempt's committed thinking plus a wire-only `(continue)` turn, asking Claude to continue exactly what its classifier had stopped. A tool call completed before a refusal was handed to the client to execute.

Claude Code ends a refused turn with a terminal error and never retries automatically. Codex retries every incomplete reason except `interrupted` and ignores `incomplete_details.retryable`; it treats the Responses failure code `invalid_prompt` as terminal.

## What Changes

- A translated refusal fails as `response.failed` with error code `invalid_prompt` and a message naming the refusal category and Anthropic's explanation, ending the turn without client retry. Non-streaming Responses and Chat return HTTP 400 `invalid_request_error`; streaming Chat emits the error event. Usage is preserved.
- Hold the first completed tool call, and every later event of the response, until the stop reason is known. Release them for any non-refusal stop; discard them on refusal so no tool from a refused turn runs or enters history.
- When a refusal follows output the client already committed, persist a hashed, client-scoped record of the refused response before the terminal event is delivered, and omit that response's items from later translated requests.
- Log the refusal category, withheld item count and delivered-output flag in the stop diagnostic. Malformed stops log status `invalid`.
- Source failure terminals record the source's own error code and message in the request log instead of a generic code.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: refusals are terminal prompt-policy failures; refused output is discarded and not replayed; refusal diagnostics.
- `model-source-routing`: failure terminals log the source's error code and message.

## Impact

Claude Responses projection, translated stream transport and non-streaming collection, translated request preparation, the existing hashed resource-provenance table and source dispatch settlement. Chat clients now receive a refusal as a 400 or error event instead of `finish_reason: content_filter`. Native Messages passthrough is unchanged. No migrations, settings or client changes.
