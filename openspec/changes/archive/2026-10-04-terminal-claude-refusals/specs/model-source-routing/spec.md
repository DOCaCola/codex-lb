## ADDED Requirements

### Requirement: Source failure terminals record the source's error
When a source stream ends with a `response.failed` or `error` terminal, the request-log row SHALL record the error code and message the source supplied in that terminal. The generic code `model_source_response_failed` SHALL apply only when the terminal carries no code. The attempt SHALL remain an error that releases its reservation, including when the client disconnects after receiving the failure.

#### Scenario: Source supplies a failure code
- **WHEN** a source ends a stream with `response.failed` carrying code `server_error` and a message
- **THEN** the request-log row records status error with code `server_error` and that message, and the reservation is released

#### Scenario: Typeless error record
- **WHEN** a source ends a stream with a typeless `{"error": {...}}` record carrying code `overloaded`
- **THEN** the request-log row records code `overloaded`

#### Scenario: Translated Claude refusal
- **WHEN** a translated Claude response fails because Claude refused
- **THEN** the request-log row records code `invalid_prompt`

#### Scenario: Failure without a code
- **WHEN** a source failure terminal carries no error code
- **THEN** the request-log row records `model_source_response_failed`
