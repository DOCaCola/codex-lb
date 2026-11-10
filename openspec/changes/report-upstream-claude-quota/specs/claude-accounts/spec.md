## ADDED Requirements

### Requirement: Upstream Claude quota refusals use the Responses usage-limit contract
The Responses projection SHALL translate confirmed upstream Claude quota-window
429 refusals into usage_limit_reached, preserving status, message, retry headers,
and attributable integer reset metadata. Unknown throttling, entitlement-only
refusals and native Messages SHALL retain their existing contracts. Default
cooldowns MUST NOT become reset metadata. Existing authorized failover and
settlement SHALL apply.

#### Scenario: Quota expires hours later
- **WHEN** upstream rejects a Responses attempt for a known five-hour quota window
- **THEN** HTTP and WebSocket errors identify usage_limit_reached with its known reset
- **AND** a client can end the turn with a quota error instead of sleeping through the reset

#### Scenario: Ordinary request throttling
- **WHEN** upstream returns a 429 without known subscription quota-window evidence
- **THEN** the error remains retryable under its existing contract

#### Scenario: Native Messages quota refusal
- **WHEN** a native Messages request receives the same upstream quota refusal
- **THEN** its native rate_limit_error contract is preserved
