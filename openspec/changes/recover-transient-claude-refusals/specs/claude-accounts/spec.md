## RENAMED Requirements

- FROM: `### Requirement: Bounded Claude overload recovery`
- TO: `### Requirement: Bounded Claude transient refusal recovery`

## MODIFIED Requirements

### Requirement: Bounded Claude transient refusal recovery
An upstream Claude refusal with status 408, 409 or any status of 500 or above, including 529, MAY be retried on the same account before generation, unless the refusal carries `x-should-retry: false`. Timeouts, local failures and invalid upstream responses MUST NOT be treated as refusals. Retries SHALL consume the shared four-send budget and fit a ten-second recovery window from dispatch entry. They SHALL share the jittered wait sequence of pre-dispatch connection recovery, starting at 250–500ms and doubling per retry; valid Retry-After SHALL be a minimum wait. Waiting SHALL be cancellable and own no admission or reservation. Repreparation SHALL enforce current authorization and history ownership. Transient refusals MUST NOT trigger credential refresh, account rotation or account/provider health penalties.

The gateway SHALL inspect SSE startup within 32 events, 64KiB and its first-frame deadline. Only comments/pings and empty message_start metadata without positive output usage MAY precede a recoverable overloaded_error. Such error SHALL surface as 529 before any public stream event. Content blocks, other generation events or positive output usage SHALL prohibit replay. Prelude-limit violations, connection failures after dispatch and timeouts MUST NOT acquire refusal retries. Exhaustion SHALL preserve the last refusal and its retry hint; partial generation SHALL retain normal failure/usage handling.

#### Scenario: Early SSE refusal
- **WHEN** HTTP 200 contains pings followed by overloaded_error before generation
- **THEN** the failed attempt closes and may retry on the same account without publishing its events

#### Scenario: Output already started
- **WHEN** overload follows a content block or positive output usage
- **THEN** the gateway does not replay the generation

#### Scenario: Wait exceeds recovery window
- **WHEN** Retry-After cannot fit the remaining recovery window
- **THEN** the original refusal is returned without shortening its requested wait

#### Scenario: Unexplained 503
- **WHEN** the first send returns a 503 with an HTML error page and the next send succeeds
- **THEN** the request completes on the same account without the client observing the refusal

#### Scenario: Anthropic declines a retry
- **WHEN** a 500 refusal carries `x-should-retry: false`
- **THEN** the refusal is returned without a retry

#### Scenario: Persistent outage
- **WHEN** every send returns a transient refusal
- **THEN** the last refusal is returned once the send budget or recovery window is exhausted

#### Scenario: Request defect
- **WHEN** the upstream returns 400
- **THEN** the refusal is returned without a retry

### Requirement: Bounded Claude pre-dispatch connection recovery
A Claude send whose connection failed before any request byte was dispatched (DNS resolution, connection refusal, connect timeout or proxy connect failure) MAY be retried on the same account. TLS verification failures and every failure after connection establishment MUST NOT be retried. Retries SHALL consume the shared four-send budget and fit the same ten-second recovery window as transient refusal recovery, sharing its wait sequence: each wait SHALL be jittered and grow per retry, starting at 250–500ms, and SHALL be cancellable and own no admission or reservation. Repreparation SHALL enforce current authorization and history ownership. Pre-dispatch recovery MUST NOT refresh credentials, rotate accounts, record cooldowns or penalize account or provider health. Exhaustion SHALL return the last connection failure.

#### Scenario: Transient DNS failure
- **WHEN** the first send fails with a DNS resolution error and the next send connects
- **THEN** the request completes on the same account without the client observing the failure

#### Scenario: TLS verification failure
- **WHEN** the send fails TLS certificate verification
- **THEN** the failure is returned without a retry

#### Scenario: Ambiguous network failure
- **WHEN** the connection drops after the request was dispatched
- **THEN** the gateway does not replay the request

#### Scenario: Persistent outage
- **WHEN** every send fails before dispatch
- **THEN** the last connection failure is returned once the send budget or recovery window is exhausted
