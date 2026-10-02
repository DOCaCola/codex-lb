## ADDED Requirements

### Requirement: Bounded Claude pre-dispatch connection recovery
A Claude send whose connection failed before any request byte was dispatched (DNS resolution, connection refusal, connect timeout or proxy connect failure) MAY be retried on the same account. TLS verification failures and every failure after connection establishment MUST NOT be retried. Retries SHALL consume the shared four-send budget and fit the same ten-second recovery window as overload recovery. Each wait SHALL be jittered and grow per retry, starting at 250–500ms, and SHALL be cancellable and own no admission or reservation. Repreparation SHALL enforce current authorization and history ownership. Pre-dispatch recovery MUST NOT refresh credentials, rotate accounts, record cooldowns or penalize account or provider health. Exhaustion SHALL return the last connection failure.

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
