# claude-accounts Delta

## MODIFIED Requirements

### Requirement: Codex protocol adaptation
Claude SHALL support Responses over downstream HTTP and WebSocket while using HTTPS/SSE upstream. Translation MUST preserve portable text, tool/custom-tool/namespace, image, reasoning and cache-usage semantics, or reject unsupported semantics explicitly. A custom tool with a lark or regex grammar format SHALL be projected as a single raw-text input whose description carries the grammar; the client remains responsible for validating that input. Claude catalog models SHALL advertise the freeform patch tool type. Truncation and pause_turn MUST NOT become completed. A refusal stop reason MUST NOT become completed; it SHALL surface as an incomplete result with reason content_filter for every translated projection, preserving output and usage. Each translated message stop SHALL log its stop reason, resulting status, upstream content block type counts and output tokens, never content, reasoning, tool input or signatures. Durable continuation MUST be persisted before terminal delivery and scoped to compatible account/model state; compaction MUST preserve useful context.

#### Scenario: Pause turn
- **WHEN** Anthropic stops with pause_turn
- **THEN** the Responses client receives an incomplete result and no hidden automatic continuation

#### Scenario: Refusal
- **WHEN** Anthropic stops with refusal on a translated Responses or Chat request, with or without visible reasoning
- **THEN** the client receives an incomplete result with reason content_filter and the turn's usage, never a completed result

#### Scenario: Stop diagnostics
- **WHEN** a translated Claude message stops
- **THEN** one log line records the stop reason, status, block type counts and output tokens without any content

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
