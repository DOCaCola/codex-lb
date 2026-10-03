## MODIFIED Requirements

### Requirement: Codex protocol adaptation
Claude SHALL support Responses over downstream HTTP and WebSocket while using HTTPS/SSE upstream. Translation MUST preserve portable text, tool/custom-tool/namespace, image, reasoning and cache-usage semantics, or reject unsupported semantics explicitly. A custom tool with a lark or regex grammar format SHALL be projected as a single raw-text input whose description carries the grammar; the client remains responsible for validating that input. Claude catalog models SHALL advertise the freeform patch tool type. Truncation, `model_context_window_exceeded` and pause_turn MUST NOT become completed; they SHALL surface as incomplete with reason max_output_tokens. A refusal stop reason MUST NOT become completed; it SHALL surface as an incomplete result with reason content_filter for every translated projection, preserving finished output and usage. A refusal MAY end the stream while content blocks or search calls are still open; that partial output SHALL be discarded: it MUST NOT receive done events and MUST NOT appear in the terminal output or continuation history, so an unfinished tool call is never delivered as executable or replayed without a result. Native passthrough SHALL forward such a refusal unchanged and record it as an incomplete terminal. Any other stop with open content, pending search calls or no stop reason SHALL fail with a message naming the open block types, pending search count and stop reason. Each translated message stop, including a failing one, SHALL log its stop reason, resulting status, upstream content block type counts and output tokens, never content, reasoning, tool input or signatures. A Claude transport failure SHALL name its exception class. Durable continuation MUST be persisted before terminal delivery and scoped to compatible account/model state; compaction MUST preserve useful context.

#### Scenario: Pause turn
- **WHEN** Anthropic stops with pause_turn
- **THEN** the Responses client receives an incomplete result with reason max_output_tokens and no hidden automatic continuation

#### Scenario: Context window exhausted
- **WHEN** Anthropic stops with model_context_window_exceeded
- **THEN** the client receives an incomplete result with reason max_output_tokens, never a completed result or an unknown-stop error

#### Scenario: Refusal
- **WHEN** Anthropic stops with refusal on a translated Responses or Chat request, with or without visible reasoning
- **THEN** the client receives an incomplete result with reason content_filter and the turn's usage, never a completed result

#### Scenario: Mid-stream refusal with an open tool call
- **WHEN** Anthropic stops with refusal while a tool call block is still open
- **THEN** the client receives no done event for that call, the terminal output omits it, and the result is incomplete with reason content_filter

#### Scenario: Native mid-stream refusal
- **WHEN** a native Messages stream stops with refusal while a content block is open
- **THEN** the stream is forwarded unchanged and settled as an incomplete terminal

#### Scenario: Unfinished non-refusal stop
- **WHEN** a stream stops with an open block or pending search under any other stop reason, or without a stop reason
- **THEN** the request fails with a message naming the open block types, pending search count and stop reason, and the stop diagnostic line is logged

#### Scenario: Stop diagnostics
- **WHEN** a translated Claude message stops
- **THEN** one log line records the stop reason, status, block type counts and output tokens without any content

#### Scenario: Transport drop
- **WHEN** the Claude connection fails before message_stop
- **THEN** the failure message names the transport exception class

#### Scenario: Grammar-format custom tool
- **WHEN** a Responses request declares a custom tool with a lark or regex grammar, such as Codex's apply_patch
- **THEN** Claude receives a tool with one required string input documenting that grammar, and its call returns to the client as a custom_tool_call carrying the raw input

#### Scenario: Patch tool advertisement
- **WHEN** a Codex client reads the model catalog
- **THEN** Claude models advertise apply_patch_tool_type freeform so the client registers its patch tool

#### Scenario: Unsupported constrained output
- **WHEN** a Responses request declares a malformed grammar, an unknown custom tool format or a provider-specific control without a Claude equivalent
- **THEN** the adapter returns an explicit unsupported-parameter error before dispatch rather than silently ignoring it

#### Scenario: Native resource history outlives provenance retention
- **WHEN** native resource history is submitted after its thirty-day resource provenance expires
- **THEN** it fails explicitly and requires portable context rather than guessing its origin from affinity
