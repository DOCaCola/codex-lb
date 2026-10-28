## ADDED Requirements

### Requirement: Model admission limits move the turn without an account penalty

An upstream refusal with error code `turn_rate_limit_exceeded` is a model admission limit: one model on one account refused until its `Retry-After`, with the account's quota intact. The proxy MUST treat it as a retryable model-capacity failure on every path that retries model capacity before downstream-visible output. A pre-created or accepted direct WebSocket replay MUST exclude the refusing account unless an owner pin or a possible hard sticky owner requires that account. The HTTP bridge MUST replay it without the selected-model capacity wait. The proxy MUST NOT record account health for it, including error counts, overload windows, rate-limit status and HTTP 429 burst backoff. When the turn cannot move, the client MUST receive the upstream refusal with its `Retry-After` unchanged.

#### Scenario: Pre-created WebSocket refusal moves to another account

- **GIVEN** two selectable accounts
- **WHEN** the first refuses a direct WebSocket `response.create` before `response.created` with `turn_rate_limit_exceeded`
- **THEN** the turn is replayed with the first account excluded and completes on the second account in one response lifecycle
- **AND** the first account's health write is a skipped `turn_rate_limit_exceeded`

#### Scenario: HTTP 429 admission limit walks the pool without waiting

- **GIVEN** two selectable accounts
- **WHEN** the first answers a streaming request with HTTP 429 code `turn_rate_limit_exceeded`
- **THEN** the request completes on the second account without a burst-backoff sleep
- **AND** the first account stays active

#### Scenario: An accepted admission refusal is replayed like capacity

- **WHEN** upstream accepts a turn and then fails it output-free with `turn_rate_limit_exceeded`
- **THEN** the direct WebSocket and the HTTP bridge replay it on another account within the single response lifecycle
