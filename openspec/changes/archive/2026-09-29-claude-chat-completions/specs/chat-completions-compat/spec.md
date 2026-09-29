## ADDED Requirements

### Requirement: Claude OAuth Chat Completions adaptation

The service SHALL route authorized Chat message requests for Claude OAuth models through the existing Claude Responses dispatch owner, without a second upstream Chat wire or duplicate API-key reservation. It MUST preserve selected model scope, retries, errors, usage settlement and disconnect cleanup. It MUST translate supported Chat controls faithfully and reject unsupported behavioral controls before dispatch. Explicit `max_completion_tokens` SHALL take precedence over `max_tokens`; both SHALL respect the discovered Claude model ceiling. `stop` SHALL map to Claude stop sequences.

#### Scenario: Text and tool turns
- **WHEN** a client requests a Claude model using Chat messages with function tools, then resends an assistant tool call and tool output
- **THEN** both turns reach Claude with the original function name, arguments and result, and return Chat-compatible completions

#### Scenario: Output controls
- **WHEN** a Claude Chat request specifies `max_completion_tokens` or `max_tokens` and `stop`
- **THEN** the preferred completion-token limit and stop sequences are applied subject to the model ceiling

#### Scenario: Reasoning ownership
- **WHEN** Claude generates reasoning for a Chat request
- **THEN** Chat output MAY expose plaintext `reasoning_content` without exposing or fabricating a Claude signature
- **AND** completed-turn plaintext `reasoning_content` SHALL be retained as ordinary assistant textual history without becoming signed reasoning
- **AND** an active tool turn SHALL restore genuine signed thinking only from a unique, unexpired replay match bound to the authenticated API key, conversation, model, account owner, full visible history and complete tool-call set
- **AND** when such a match is unavailable, the affected tool cycle SHALL be reconstructed as ordinary conversation from caller-visible reasoning, assistant text, tool identities/arguments, and paired results, without native tool-use or fabricated signed blocks
- **AND** reconstruction SHALL preserve supported content blocks and turn ordering, keep requested reasoning and tool declarations for new calls, and reject unrepresentable content rather than discard it

#### Scenario: Replay completion boundary
- **WHEN** a Claude Chat tool response completes, including during SSE streaming
- **THEN** the service MUST attempt authenticated replay retention before the completed tool turn is exposed to the client; a failed store write MUST leave the next turn on the caller-visible reconstruction path
- **AND** interrupted or incomplete streams SHALL NOT be advertised as completed retained turns

#### Scenario: Reconstructed tool history
- **WHEN** signed replay is missing, expired, anonymous, ambiguous, model-incompatible, or belongs to another client or unavailable account
- **THEN** only caller-visible Chat history SHALL be used to reconstruct the affected cycle as assistant textual history and quoted user result data
- **AND** each tool name, call ID, argument and result SHALL remain paired and ordered, including parallel and empty results
- **AND** the gateway SHALL NOT ask Claude to rerun already-executed historical calls, promote results to system instructions, expose hidden/redacted state, or treat this representation as native semantic equivalence

#### Scenario: Thinking display
- **WHEN** an adaptive-capable Claude model receives enabled Chat reasoning without a hide request
- **THEN** the Messages request SHALL ask for summarized thinking display
- **AND** `thinking.display: "omitted"` SHALL suppress Chat reasoning output

#### Scenario: Streaming and incomplete output
- **WHEN** Claude emits text, tools, usage, an unknown incomplete reason or an upstream error
- **THEN** Chat streaming or JSON output preserves usable data and usage, and never turns an unknown incomplete or error into a successful stop

#### Scenario: Existing routes
- **WHEN** an OpenAI-compatible Chat request or native Claude Messages request is sent
- **THEN** its existing routing and wire behavior is unchanged
