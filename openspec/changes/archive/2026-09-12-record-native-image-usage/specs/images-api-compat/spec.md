## ADDED Requirements

### Requirement: Native image usage has one accounting owner
Native image requests MUST parse successful upstream usage once into a request-owned typed record before settlement. Both API-key settlement and request logs MUST consume that record's public model, input tokens, output tokens and cached input tokens. Reported usage MUST be persisted even without an API-key reservation so existing request-log pricing can calculate API-equivalent cost. Missing or invalid usage and failed responses MUST NOT fabricate token counts. Raw native response bytes, status, retries and account cleanup MUST remain unchanged.

#### Scenario: Native generation or edit reports usage
- **WHEN** a successful native image response reports input, output and cached input tokens
- **THEN** the request log and applicable API-key settlement use the same counts and the request-log API exposes the existing model-price estimate

#### Scenario: No token usage is available
- **WHEN** upstream omits usage, reports invalid usage or fails the request
- **THEN** request-log token counts remain null and image reservations retain their existing release behavior
