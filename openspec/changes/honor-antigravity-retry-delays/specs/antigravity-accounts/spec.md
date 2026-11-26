## ADDED Requirements

### Requirement: Antigravity retry delays
For 429 and overload rejections the retry delay SHALL come from `google.rpc.RetryInfo`, falling back to the HTTP `Retry-After` (seconds, an explicit 0, or an HTTP date). A bare `RESOURCE_EXHAUSTED` MUST stay unexplained whatever its header delay. A rate limit or overload delay of at least 3 seconds SHALL cool that model on that account; shorter ones are waited out in place.

#### Scenario: Capacity delay
- **WHEN** Cloud Code answers 503 `MODEL_CAPACITY_EXHAUSTED` with a 17-second delay in RetryInfo or `Retry-After`
- **THEN** the model is cooled on that account for 17 seconds and the request moves once to another account

#### Scenario: Header-only rate limit
- **WHEN** a `RATE_LIMIT_EXCEEDED` 429 carries no RetryInfo and `Retry-After: 600`
- **THEN** it is classified as quota exhaustion resetting in 10 minutes

### Requirement: Rate-limited Antigravity metadata pacing
A rate-limited metadata endpoint SHALL next be due after Google's classified delay, or after its normal refresh interval when Google gives none.

#### Scenario: Metadata 429 without a delay
- **WHEN** the quota endpoint answers 429 without RetryInfo or `Retry-After`
- **THEN** it is not due again before the quota refresh interval
