## MODIFIED Requirements

### Requirement: Model admission limits move the turn without an account penalty

An upstream refusal with error code `turn_rate_limit_exceeded` is a model admission limit: one model on one account refused until its `Retry-After`, with the account's quota intact. The proxy MUST treat it as a retryable model-capacity failure on every path that retries model capacity before downstream-visible output. The proxy MUST record a cooldown for that model on the refusing account where the refusal is first recognized, lasting the refusal's `Retry-After`, 15 seconds when none is given, and at most 600 seconds; a later refusal MUST NOT shorten an active cooldown. While it is active, selection for that model MUST skip the account for fresh selection and MUST release a soft sticky owner for that request without deleting its mapping; a hard owner MUST stay selected, and the cooldown MUST NOT empty the candidate pool. The HTTP bridge MUST replay it without the selected-model capacity wait. The proxy MUST NOT record account health for it, including error counts, overload windows, rate-limit status and HTTP 429 burst backoff. When an anchored turn cannot leave the refusing owner, the client MUST receive a failure with code `turn_rate_limit_exceeded` and upstream's message and no `Retry-After`, so it retries without the anchor. When every candidate account is cooling, the client MUST receive the upstream refusal with its `Retry-After` unchanged.

#### Scenario: Pre-created WebSocket refusal moves to another account

- **GIVEN** two selectable accounts
- **WHEN** the first refuses a direct WebSocket `response.create` before `response.created` with `turn_rate_limit_exceeded`
- **THEN** the first account cools for that model and the turn completes on the second account in one response lifecycle
- **AND** the first account's health write is a skipped `turn_rate_limit_exceeded`

#### Scenario: HTTP 429 admission limit walks the pool without waiting

- **GIVEN** two selectable accounts
- **WHEN** the first answers a streaming request with HTTP 429 code `turn_rate_limit_exceeded` and `Retry-After`
- **THEN** the request completes on the second account without a burst-backoff sleep
- **AND** the first account stays active, has no burst cooldown and cools for that model until `Retry-After`
- **AND** the next request for that model selects the second account directly

#### Scenario: An accepted admission refusal is replayed like capacity

- **WHEN** upstream accepts a turn and then fails it output-free with `turn_rate_limit_exceeded`
- **THEN** the direct WebSocket and the HTTP bridge replay it on another account within the single response lifecycle

#### Scenario: Soft sticky owner is released while its model cools

- **GIVEN** a conversation with a prompt-cache, sticky-thread or Codex-session owner whose model is cooling
- **WHEN** the next turn for that model is selected
- **THEN** another account serves it and the sticky mapping is kept

#### Scenario: Cooldown is scoped to the refused model

- **GIVEN** an account cooling for one model
- **WHEN** a request for a different model is selected
- **THEN** the account remains selectable

#### Scenario: Anchored turn refused by its owner is retried promptly

- **WHEN** a turn anchored to its previous response's owner is refused with `turn_rate_limit_exceeded` and cannot move
- **THEN** the client receives `response.failed` with code `turn_rate_limit_exceeded` and upstream's message
- **AND** the client's resend without the anchor is served by another account
