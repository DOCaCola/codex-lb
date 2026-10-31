## MODIFIED Requirements

### Requirement: Observed reset events
The service SHALL detect scheduled, unexpected and redeemed native OpenAI quota resets from
fresh authoritative usage snapshots. Missing data, first samples and identity/plan/window
changes MUST NOT create reset events. Unexpected
resets MUST include same-deadline drops and exclude ordinary rolling deadline creep.
An unexpected reset SHALL be reported as redeemed when codex-lb recorded a reset-credit
redemption for the account after the previous observation and no later than the new one.
Every reset-credit consume path SHALL record the redemption before calling upstream.
Each account/window transition SHALL produce one durable event without consolidation.

#### Scenario: Unexpected replenishment
- **WHEN** used quota falls substantially before its scheduled deadline
- **THEN** one unexpected event records before/after usage and observation time

#### Scenario: Redeemed reset credit
- **WHEN** an operator or client redeems a reset credit and the next observation shows the drop
- **THEN** one redeemed event records before/after usage and observation time

#### Scenario: Earlier redemption
- **WHEN** a reset is observed after a redemption that preceded the previous observation
- **THEN** the reset is reported as unexpected

#### Scenario: Repeated observations
- **WHEN** replicas refresh the same unchanged post-reset quota
- **THEN** they do not enqueue additional reset notifications

### Requirement: Secure operator configuration
Settings SHALL offer one optional HTTP or HTTPS destination, event-kind filters for scheduled,
unexpected and redeemed resets, optional HMAC signing, test delivery and status. Secrets MUST
be encrypted and masked.
Private and loopback destinations SHALL be allowed without DNS address filtering.
Redirects MUST NOT be followed. Only
authorized dashboard administrators SHALL configure or test delivery.

#### Scenario: Private DNS resolution
- **WHEN** a configured hostname resolves to a private address during delivery
- **THEN** delivery uses normal DNS resolution and may connect to that address

#### Scenario: Filter redemptions
- **WHEN** an administrator deselects redeemed resets
- **THEN** redemptions observed between samples enqueue no event
