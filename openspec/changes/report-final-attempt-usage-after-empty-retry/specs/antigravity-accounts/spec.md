## MODIFIED Requirements

### Requirement: Antigravity response projection
Gemini SSE events SHALL be unwrapped and projected into Responses events: thought text to reasoning summaries, text to output text and function calls to function or custom tool calls with stable IDs. Usage SHALL map prompt, cached, candidate and thought token counts to input, cached input, output and reasoning tokens. `STOP` SHALL complete, `MAX_TOKENS` SHALL be incomplete with `max_output_tokens`, safety finish reasons SHALL be incomplete with `content_filter`, and malformed or unexpected tool calls SHALL fail without exposing an executable call. A completion without visible text or tool call SHALL be retried once on the same account before output, then fail explicitly. After that retry the client's usage SHALL be the final attempt's, the context it continues from, while the request is billed for both attempts, including when both are empty.

#### Scenario: Empty completion
- **WHEN** Gemini stops with only thought parts twice
- **THEN** the client receives an explicit empty-completion error after one retry
- **AND** the request is billed for both attempts

#### Scenario: Retried empty completion reports the final attempt's usage
- **WHEN** Gemini stops with only thought parts and the retry answers with text
- **THEN** the client's usage equals the retry's usage alone
- **AND** the request is billed for the input and output tokens of both attempts
