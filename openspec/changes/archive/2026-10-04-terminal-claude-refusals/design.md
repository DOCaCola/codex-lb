# Design

## Context

Codex maps `response.incomplete` with reason `content_filter` to a retryable content-filter error and records guidance before retrying (`core/src/responses_retry.rs`). Every other incomplete reason except `interrupted` is a retryable stream error. `response.failed` with `error.code = "invalid_prompt"` maps to `InvalidPrompt`, which has no retry delay and ends the turn. Codex ignores `incomplete_details.retryable`.

Codex records a response item in history when its `response.output_item.done` arrives and dispatches tool calls at that point. It tracks one active output item, so a done event must precede the next item's `output_item.added`. Text has to stream live. A stream therefore cannot withhold everything until the stop reason, and a refusal after a finished thinking or text block necessarily follows output the client already committed. Codex resends committed items with the ids the gateway assigned (`resp_<message>_<index>`).

## Decisions

1. **Refusal is a terminal prompt-policy failure.** The projection ends a refused turn with `response.failed`, `error = {code: "invalid_prompt", message}`. The message names the bounded `stop_details.category` and appends Anthropic's `explanation` for display; the explanation is never parsed or logged. This matches Claude Code's terminal refusal and Anthropic's guidance to change the request or model. Non-streaming collection raises a 400 `invalid_request_error` carrying the same error; Chat inherits it.
2. **Tool calls wait for the stop reason.** From the first completed tool call onward, all events are held. Claude ends a tool turn immediately after its last call, so this adds no meaningful latency, and a refused turn never yields an executable call. On refusal the held events are dropped, their items are removed from the terminal output, and the terminal takes the first dropped sequence number so numbering stays contiguous.
3. **Committed refused output is recorded, then omitted.** When the refused response delivered any done item, `sha256([client_scope, "refused_response", response_id])` is written to `claude_resource_origins` before the terminal event is yielded. The record is not model-bound. Translated preparation drops every input item of a refused response and refreshes the record's thirty-day retention while that history is still sent. When the user continues the conversation, Claude sees it without the refused attempt.
4. **Failure terminals keep the source's error.** Source dispatch captures the code and message of a `response.failed` or `error` terminal and records them on the request-log row; the generic `model_source_response_failed` applies only when the source supplied none. Refusals thus appear as `invalid_prompt`.
5. **Native passthrough is unchanged.** A native Messages client receives Claude's refusal stop as sent and handles it itself; settlement records it as incomplete.

## Alternatives considered

- `incomplete` with `retryable: false` (opencodex #4312) does not stop current Codex, which ignores that field.
- Delaying only done events until the stop reason breaks Codex's active-item tracking; holding all events stops text from streaming after thinking.
- Matching Codex's `<content_filter_guidance>` marker was rejected: it couples to client prompt text and cannot identify which items belonged to the refused response.

## Risks

- Chat clients that relied on `finish_reason: content_filter` now receive an error; this matches OpenAI's prompt-policy behaviour.
- A recording failure surfaces as the existing explicit provenance stream error.
- After thirty days without use a record expires and that output would be replayed again; active use keeps it alive.
