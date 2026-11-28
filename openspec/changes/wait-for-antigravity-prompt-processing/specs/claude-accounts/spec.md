## ADDED Requirements

### Requirement: Claude first-frame timeout reporting
When a streamed Claude request receives response headers but no SSE frame within the first-frame deadline, the request
SHALL fail with `model_source_timeout` and a message naming the deadline that applied. A stream that ends or goes
idle before its first frame SHALL fail with `invalid_upstream_response`.

#### Scenario: Silent first frame
- **WHEN** Anthropic sends response headers but no SSE frame within the first-frame deadline
- **THEN** the request fails with `model_source_timeout` rather than `invalid_upstream_response`
