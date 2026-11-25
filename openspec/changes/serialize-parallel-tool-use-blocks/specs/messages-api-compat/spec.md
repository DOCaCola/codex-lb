## MODIFIED Requirements

### Requirement: Messages response projection

Translated output SHALL be a valid Messages stream:

- `message_start` echoes the client-facing model;
- each reasoning item becomes exactly one thinking block, closed with its signature;
- text becomes text blocks;
- each function call becomes exactly one `tool_use` block, whose start waits until the name is known;
- hosted web search becomes `server_tool_use` and `web_search_tool_result` blocks;
- one `message_delta` and one `message_stop` end the stream.

Content blocks SHALL NOT interleave. At most one `tool_use` block SHALL be open at a time. A function call announced
while another tool block is open SHALL wait, in announcement order, with its argument deltas buffered. It SHALL start
when no tool block is open. A call that has already finished SHALL be emitted whole with its final arguments. Calls still waiting when
the response completes SHALL be emitted with the arguments received.

Stop reasons SHALL map as follows: a function call to `tool_use`, the output limit to `max_tokens`, a content filter
to `refusal`, and otherwise `end_turn`. `input_tokens` SHALL exclude
cache reads and writes, which SHALL be reported separately. Reasoning tokens SHALL be included in output tokens.

#### Scenario: Tool turn
- **WHEN** the model calls a function after reasoning
- **THEN** the client receives a signed thinking block, one complete `tool_use` block and stop reason `tool_use`

#### Scenario: Parallel calls with overlapping events
- **WHEN** the model announces two function calls before either finishes, and their argument deltas interleave
- **THEN** the client receives exactly two `tool_use` blocks, in announcement order and each with its complete input
- **AND** every delta targets the block that is currently open

#### Scenario: Later call finishes first
- **WHEN** the second of two parallel calls finishes before the first
- **THEN** the second call's block is emitted, whole, after the first call's block closes

#### Scenario: Cached usage
- **WHEN** upstream reports 10,000 input tokens with 8,000 cached
- **THEN** the client receives `input_tokens` 2,000 and `cache_read_input_tokens` 8,000
