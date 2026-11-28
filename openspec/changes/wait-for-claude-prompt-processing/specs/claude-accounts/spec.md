## ADDED Requirements

### Requirement: Claude prompt processing before response headers
A streamed Claude request SHALL wait up to 180 seconds for Anthropic's response headers before failing with
`model_source_timeout`, independent of the Responses model-source header deadline. Connection establishment, the
first-frame deadline after headers, the stream idle cap and client cancellation SHALL still apply. The timeout
message SHALL state the deadline that applied.

#### Scenario: Large prompt
- **WHEN** Anthropic sends response headers 60 seconds after a streamed Claude request is sent
- **THEN** the request continues and streams the response

#### Scenario: Silent upstream
- **WHEN** Anthropic sends no response headers within 180 seconds
- **THEN** the request fails with `model_source_timeout` and a message naming 180s
