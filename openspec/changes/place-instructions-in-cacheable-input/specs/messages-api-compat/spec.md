## MODIFIED Requirements

### Requirement: Messages request translation

The translator SHALL map:

- system text blocks, in order, to one leading developer input message with one text part per block, removing
  Claude Code's billing attribution line and leaving top-level instructions empty, because from GPT-6.2 on top-level
  instructions are never prompt-cached;
- message-level system content to developer messages, placed after the outputs of any tool calls still pending at
  that point, with one text part per block;
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

#### Scenario: System prompt placement
- **WHEN** a translated request carries system text blocks
- **THEN** upstream receives them as the first input item, a developer message with one text part per block
- **AND** top-level `instructions` is `""`

#### Scenario: Unsupported server tool
- **WHEN** a translated request declares an Anthropic server tool other than web search
- **THEN** it fails before dispatch with `invalid_request_error` naming the tool type

#### Scenario: Stop sequences
- **WHEN** a translated request carries non-empty `stop_sequences`
- **THEN** it fails before dispatch with `invalid_request_error` naming the field

### Requirement: Messages identity and token counting

The session SHALL come from `x-claude-code-session-id` or `metadata.user_id`, rejecting disagreement. The agent SHALL
come from `x-claude-code-agent-id`, defaulting to the main agent. The prompt-cache key SHALL be a hash of model,
session and agent, so account stickiness follows it. Request logs SHALL record the Claude Code session as the
conversation. Without a session, the prompt-cache key SHALL hash the model, the system text and the translated tools
in wire order. `count_tokens` for a translated model SHALL return a local estimate of the
translated request without selecting an account, reserving API-key budget or contacting upstream.

#### Scenario: Subagent isolation
- **WHEN** a parent agent and a subagent in one Claude Code session use the same model
- **THEN** they receive distinct prompt-cache keys

#### Scenario: Token count
- **WHEN** Claude Code counts tokens for a GPT model
- **THEN** it receives an estimate and no upstream or account activity occurs

