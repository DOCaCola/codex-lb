# Chat Completions Compatibility Context

## Purpose and Scope

This capability aligns `POST /v1/chat/completions` with OpenAI’s expectations by mapping chat requests to Responses, preserving streaming behavior, and returning OpenAI-compatible error envelopes.

See `openspec/specs/chat-completions-compat/spec.md` for normative requirements.

Claude OAuth Chat requests use the same Responses-to-Claude source dispatcher as `/v1/responses`. The Chat route projects Messages output into Chat JSON or SSE after the dispatcher has acquired its admission and usage owner. For example, `max_completion_tokens: 17` and `stop: ["END"]` become a 17-token Claude Messages cap and `stop_sequences: ["END"]`; the existing account selection and quota recovery still apply.

Claude Chat `reasoning_content` is caller-visible plaintext, not a Claude signature. Completed plaintext reasoning becomes ordinary assistant text. Signed thinking remains in the private Responses continuation store and is never reconstructed from that text. For an active tool cycle, a keyed client can resend its exact visible Chat history and all tool results; the gateway locates a unique live record under the same key and conversation, authenticates its account/model-bound signed blocks, and restores those blocks before forwarding. If replay is missing, ambiguous, expired, cross-key, model-incompatible, or owned by an unavailable account, the affected cycle becomes ordinary assistant text plus quoted user result data, preserving call identities, arguments, results and supported images. This representation preserves visible information and ordering but is not semantically identical to native Claude tool-use. It neither fabricates a signature nor asks Claude to execute historical calls again. New reasoning requests may declare tools, including `tool_choice: none`. Adaptive-capable models request summarized thinking unless `thinking.display: "omitted"` hides it. `pause_turn` and other unknown incomplete reasons become errors rather than successful Chat stops. Chat usage includes cache reads and cache creation details when Claude reports them.

For both JSON and SSE, retention is attempted before the completion reaches the client. A store failure is logged without failing the completed model response; a subsequent Chat turn reconstructs from visible content because no authenticated record exists. Incomplete or interrupted streams do not seed completed Chat tool replay.

## Rationale and Decisions

- **Mapping to Responses:** Chat Completions are derived from the Responses stream to keep behavior consistent across endpoints.
- **Responses-shaped passthrough:** Some OpenAI-compatible clients send `input` through `/v1/chat/completions`; those payloads are treated as Responses requests after chat-level validation.
- **Strict role/content rules:** System/developer messages are text-only; user content parts are validated for supported types.
- **Usage streaming:** When `stream_options.include_usage` is enabled, usage appears in the final chunk while earlier chunks include `usage: null`.
- **Obfuscation passthrough:** `stream_options.include_obfuscation` is forwarded to upstream when present.

## Constraints

- Oversized image data URLs (>8MB) are dropped from user inputs.
- Audio input (`input_audio`) is not supported and is rejected.
- Built-in Responses tools are preserved only on the Responses-shaped passthrough path; ordinary chat-message payloads keep the narrower chat tool policy.
- Omitted top-level `tools` stay omitted on the mapped Responses payload. `default_factory=list` plus an unconditional `to_responses_request()` write used to synthesize `"tools": []` and mark the field as set, which bypassed the Responses omit path (issue #1184). An explicit client-sent `[]` is still forwarded.
- `response_format` is translated to `text.format` with JSON schema validation.

## Failure Modes

- **Upstream stream failure:** Emit an error chunk, then terminate with `data: [DONE]`.
- **Non-stream failures:** Return an OpenAI error envelope. HTTP status follows
  the same map as non-stream `/v1/responses` (`429` for `rate_limit_exceeded`,
  not a blanket 502). The upstream Responses generator is closed so reservation
  finalizers run even when the first collected event is `response.failed`.
- **Invalid content types:** Reject with `invalid_request_error`.

## Examples

Streaming request with usage:

```json
{
  "model": "gpt-5.2",
  "messages": [{"role": "user", "content": "hi"}],
  "stream": true,
  "stream_options": { "include_usage": true }
}
```

Responses-shaped chat request with a built-in tool:

```json
{
  "model": "gpt-5.2",
  "input": [{"role": "user", "content": [{"type": "input_text", "text": "Generate an image."}]}],
  "tools": [{"type": "image_generation"}],
  "tool_choice": {"type": "image_generation"}
}
```

## Operational Notes

- Streaming chunk mapping is validated in unit tests.
- Integration tests cover include_usage and tool call finish reasons.
