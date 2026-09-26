## ADDED Requirements

### Requirement: Observed reset events
The service SHALL detect scheduled and unexpected native OpenAI quota resets from
fresh authoritative usage snapshots. Missing data, first samples, identity/plan/window
changes and known redemption intervals MUST NOT create reset events. Unexpected
resets MUST include same-deadline drops and exclude ordinary rolling deadline creep.
Each account/window transition SHALL produce one durable event without consolidation.

#### Scenario: Unexpected replenishment
- **WHEN** used quota falls substantially before its scheduled deadline
- **THEN** one unexpected event records before/after usage and observation time

#### Scenario: Repeated observations
- **WHEN** replicas refresh the same unchanged post-reset quota
- **THEN** they do not enqueue additional reset notifications

### Requirement: Isolated webhook delivery
Delivery SHALL run outside inference and snapshot transactions with expiring claims,
bounded retries and stable event IDs. Receivers MUST be told delivery can repeat.
Disabled or changed destinations MUST cancel pending old-generation events.

#### Scenario: Temporary receiver failure
- **WHEN** delivery returns a retryable error
- **THEN** retry preserves the event ID and body within a finite attempt/time budget

### Requirement: Secure operator configuration
Settings SHALL offer one optional HTTPS destination, event-kind filters, optional
HMAC signing, test delivery and status. Secrets MUST be encrypted and masked.
Non-public destinations and redirects MUST be blocked at connection time. Only
authorized dashboard administrators SHALL configure or test delivery.

#### Scenario: Private DNS resolution
- **WHEN** a configured hostname resolves to a private address during delivery
- **THEN** delivery is rejected without contacting that address
