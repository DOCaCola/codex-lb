# messages-api-compat Specification

## Purpose

Let Anthropic Messages clients such as Claude Code use Responses models, served by OpenAI accounts and Responses
model sources through the same dispatch as `/v1/responses`, while Claude models keep the native Claude route.

## Requirements

### Requirement: Messages routing by model

Authenticated `/v1/messages` and `/v1/messages/count_tokens` SHALL first decode a `clb-claude-` model alias to the model it names: `~s` becomes `/` and `~t` becomes `~`, and any other `~` sequence or an empty name SHALL fail with an Anthropic `invalid_request_error`. They SHALL then apply the API key's enforced model. Model names starting with `anthropic/` or `claude-` SHALL use the native Claude route. Any other name SHALL be resolved as a Responses model the API key may use, served by a native account or an enabled Responses-capable model source, and SHALL be served by translation. A model the API key may not use SHALL fail before dispatch with an Anthropic `permission_error`. Any other failure to serve the model SHALL be the error `/v1/responses` returns for it, as an Anthropic error envelope. No Claude account is selected for a translated model. Request logs, limits, pricing and reasoning envelopes SHALL use the routed model; the response SHALL report the model as the client sent it.

#### Scenario: Claude Code requests a GPT model
- **WHEN** Claude Code sends a Messages request for `gpt-6.1-sol`
- **THEN** the request is served by an OpenAI account through translation and no Claude account is selected

#### Scenario: Claude Code requests a discovered alias
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt-6.1-sol`
- **THEN** the request is served and logged as `gpt-6.1-sol`
- **AND** the response reports the model `clb-claude-gpt-6.1-sol`

#### Scenario: Invalid alias
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt~x`
- **THEN** the client receives an Anthropic `invalid_request_error` before any upstream request

#### Scenario: Claude model unchanged
- **WHEN** Claude Code sends a Messages request for `claude-opus-5-5`
- **THEN** it uses the native Claude route as before

#### Scenario: Unauthorized model
- **WHEN** the API key's allowed models exclude the requested non-Claude model
- **THEN** the client receives an Anthropic `permission_error` before any upstream request

#### Scenario: Unknown model
- **WHEN** the model resolves to neither a Claude model nor a model any account or source serves
- **THEN** the client receives the `/v1/responses` error for that model as an Anthropic error envelope

### Requirement: Translated Messages share Responses dispatch

A translated Messages request SHALL become one Responses request dispatched by the same owner as `/v1/responses`.
That owner provides account and source selection, stickiness, API-key reservations and limits, fast-mode policy,
encrypted-content recovery, request logging and pricing. The translation MUST NOT use a separate upstream client. The
upstream request SHALL stream with `store: false` and include encrypted reasoning. A non-streaming client SHALL
receive the aggregated Messages response. Request logs SHALL identify the Messages ingress and record the
client-facing model.

#### Scenario: OpenRouter model from Claude Code
- **WHEN** Claude Code requests a model served by an enabled OpenRouter source
- **THEN** the request is routed, limited, logged and priced as the equivalent Responses request

### Requirement: Messages request translation

The translator SHALL map:

- system text blocks, in order, to instructions, removing Claude Code's billing attribution line;
- message-level system content to developer messages, placed after the outputs of any tool calls still pending at
  that point;
- text, base64 and URL images, and base64 PDF documents to Responses input parts;
- `tool_use` and `tool_result`, including result images, to function calls and outputs with stable call IDs;
- tools to non-strict function tools with JSON Schema dialect keywords and unsupported patterns removed;
- `tool_choice` and `disable_parallel_tool_use`;
- `max_tokens`, `temperature`, `top_p` and `output_config.format` to their Responses fields, subject to existing
  destination normalization;
- `speed: fast` to the priority service tier, subject to fast-mode policy.

Tool names and call IDs longer than 64 characters SHALL use deterministic request-local aliases restored in the
output. Cache markers, `defer_loading`, `context_management` and beta headers SHALL NOT be forwarded. Anthropic web
search SHALL map to hosted web search. Any other server tool SHALL be rejected before dispatch with
`invalid_request_error`. Replayed `server_tool_use` and `web_search_tool_result` blocks SHALL be omitted; the
answer text that used them is already part of the history. Non-empty `stop_sequences`, `top_k`, `mcp_servers` and
`container` have no Responses equivalent and SHALL be rejected before dispatch with `invalid_request_error`.

#### Scenario: Long MCP tool name
- **WHEN** a request declares and replays a tool whose name exceeds 64 characters
- **THEN** upstream receives the same alias in the declaration and history, and the client receives the original name

#### Scenario: Unsupported server tool
- **WHEN** a translated request declares an Anthropic server tool other than web search
- **THEN** it fails before dispatch with `invalid_request_error` naming the tool type

#### Scenario: Stop sequences
- **WHEN** a translated request carries non-empty `stop_sequences`
- **THEN** it fails before dispatch with `invalid_request_error` naming the field

### Requirement: Messages reasoning controls

`output_config.effort` SHALL pass through as the reasoning effort. Otherwise, an enabled thinking budget SHALL map
to an effort bucket: up to 512 tokens is minimal, up to 1024 low, up to 8192 medium, up to 24576 high, and above that
xhigh. Disabled thinking SHALL map to `none`. Adaptive thinking without an effort SHALL leave effort unset. Existing
per-model effort normalization and API-key effort policy SHALL apply afterwards. Reasoning summaries SHALL be requested
unless thinking is disabled or its display is omitted.

#### Scenario: Claude Code effort command
- **WHEN** Claude Code sends adaptive thinking with `output_config.effort: high`
- **THEN** the upstream request carries reasoning effort `high`

### Requirement: Messages reasoning continuity

Each upstream reasoning item SHALL be returned as a thinking block whose text is its summary and whose signature is a
versioned proxy envelope. The envelope SHALL hold the encrypted content, the item ID and the client-facing model, and
SHALL be authenticated with an installation-keyed HMAC. On replay, a valid envelope for the requested model SHALL
become a reasoning item with its encrypted content and original ID. Envelopes for another model, foreign signatures,
unsigned thinking and redacted thinking SHALL be omitted. A malformed or unauthenticated envelope SHALL fail with
`invalid_request_error`. Commentary-phase messages SHALL be returned as unsigned thinking blocks.

#### Scenario: Multi-turn reasoning
- **WHEN** Claude Code replays a GPT turn's thinking block to the same model
- **THEN** upstream receives the original encrypted reasoning item

#### Scenario: Model switch inside a session
- **WHEN** history contains envelopes from another model
- **THEN** those thinking blocks are omitted and the request proceeds

#### Scenario: Forged envelope
- **WHEN** an envelope's authentication tag does not verify
- **THEN** the request fails with `invalid_request_error` before dispatch

### Requirement: Messages response projection

Translated output SHALL be a valid Messages stream:

- `message_start` echoes the client-facing model;
- each reasoning item becomes exactly one thinking block, closed with its signature;
- text becomes text blocks;
- function calls become `tool_use` blocks whose start waits until the name is known;
- hosted web search becomes `server_tool_use` and `web_search_tool_result` blocks;
- one `message_delta` and one `message_stop` end the stream.

Stop reasons SHALL map as follows: a function call to `tool_use`, the output limit to `max_tokens`, a content filter
to `refusal`, and otherwise `end_turn`. `input_tokens` SHALL exclude
cache reads and writes, which SHALL be reported separately. Reasoning tokens SHALL be included in output tokens.

#### Scenario: Tool turn
- **WHEN** the model calls a function after reasoning
- **THEN** the client receives a signed thinking block, one complete `tool_use` block and stop reason `tool_use`

#### Scenario: Cached usage
- **WHEN** upstream reports 10,000 input tokens with 8,000 cached
- **THEN** the client receives `input_tokens` 2,000 and `cache_read_input_tokens` 8,000

### Requirement: Messages error projection

The proxy SHALL withhold `message_start` until the first upstream output event or terminal. A failure before output
SHALL be an HTTP error with an Anthropic error envelope:

- context overflow: 400 `invalid_request_error` whose message begins "prompt is too long";
- quota or rate limit: 429 `rate_limit_error` with `retry-after` when known;
- overload: 529 `overloaded_error`;
- authentication or permission failure: 401 or 403;
- any other client error: `invalid_request_error`;
- any other upstream failure: `api_error`.

A failure after output SHALL be an in-band `error` event with no `message_stop`.

#### Scenario: Overflow triggers compaction
- **WHEN** upstream rejects a translated request with `context_length_exceeded` before output
- **THEN** the client receives HTTP 400 `invalid_request_error` "prompt is too long" and no `message_start`

#### Scenario: Mid-stream failure
- **WHEN** upstream fails after text was streamed
- **THEN** the client receives an `error` event and no `message_stop`

### Requirement: Messages identity and token counting

The session SHALL come from `x-claude-code-session-id` or `metadata.user_id`, rejecting disagreement. The agent SHALL
come from `x-claude-code-agent-id`, defaulting to the main agent. The prompt-cache key SHALL be a hash of model,
session and agent, so account stickiness follows it. Request logs SHALL record the Claude Code session as the
conversation. Without a session, the prompt-cache key SHALL hash the model, the instructions and the translated tools
in wire order. `count_tokens` for a translated model SHALL return a local estimate of the
translated request without selecting an account, reserving API-key budget or contacting upstream.

#### Scenario: Subagent isolation
- **WHEN** a parent agent and a subagent in one Claude Code session use the same model
- **THEN** they receive distinct prompt-cache keys

#### Scenario: Token count
- **WHEN** Claude Code counts tokens for a GPT model
- **THEN** it receives an estimate and no upstream or account activity occurs

### Requirement: Claude Code Fast selectors for OpenAI models

Claude Code discovery SHALL list, directly after each listed OpenAI account model whose catalog offers the priority
service tier, a sibling entry with the ID `clb-claude-<escaped model>~fast`, the display name and description
suffixed with ` · Fast`, and the same limits. Fast entries SHALL NOT be listed while Fast Mode is prohibited or when
the API key enforces a service tier, and SHALL NOT be listed for model-source or Claude models. Decoding SHALL treat a
terminal `~fast` as the Fast marker before decoding the escaped name. A Messages request naming a Fast selector SHALL
be served as the named model with `service_tier: "priority"`, subject to Fast Mode policy; a Fast selector for a
model whose catalog does not offer the priority tier SHALL fail before dispatch with `invalid_request_error`.

#### Scenario: Fast row listed
- **WHEN** Claude Code discovers models and `gpt-5.6-sol` offers the priority tier
- **THEN** `clb-claude-gpt-5.6-sol~fast` follows `clb-claude-gpt-5.6-sol` with a ` · Fast` display name

#### Scenario: Fast selector served
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt-5.6-sol~fast`
- **THEN** upstream receives `gpt-5.6-sol` with `service_tier: "priority"`
- **AND** the response reports `clb-claude-gpt-5.6-sol~fast`

#### Scenario: Model without Fast
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt-5.4~fast` and `gpt-5.4` offers no priority tier
- **THEN** it receives `invalid_request_error` before any upstream request

#### Scenario: Fast Mode prohibited
- **WHEN** Fast Mode is prohibited
- **THEN** discovery lists no Fast entries
