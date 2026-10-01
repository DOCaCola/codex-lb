## ADDED Requirements

### Requirement: Streamed tool calls without arguments keep their declared input
The Claude Responses stream projection SHALL treat an empty `input_json_delta` fragment as carrying no input: it SHALL NOT be buffered or forwarded as a client argument delta. When a tool block streams no argument JSON, its input SHALL be the `input` from `content_block_start` and SHALL be decoded and validated exactly as a non-streamed block. Non-empty argument JSON that does not parse SHALL fail the response.

#### Scenario: Function tool without arguments
- **WHEN** Claude starts a function tool block with input `{}` and streams only an empty argument fragment
- **THEN** the client receives a completed `function_call` with arguments `{}` and no empty argument delta

#### Scenario: Wrapped tool without arguments
- **WHEN** a tool whose schema needs the arguments envelope streams no argument JSON
- **THEN** the response fails with the tool's invalid arguments envelope error

#### Scenario: Malformed argument JSON
- **WHEN** a tool block streams non-empty argument JSON that does not parse
- **THEN** the response fails with an invalid tool JSON error
