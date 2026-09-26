# Quota reset webhook

## Purpose

Notify operators of observed native OpenAI account quota replenishment through an
optional secure HTTP webhook.

## Requirements

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

### Requirement: Destination draft visibility
The URL editor SHALL mask input by default and offer an accessible show/hide control
for the local draft only. Saving SHALL clear the draft and restore masking without
retrieving the stored destination.

#### Scenario: Inspect a destination before saving
- **WHEN** an operator toggles draft visibility
- **THEN** the entered URL is revealed or masked without changing its value or saving

### Requirement: Explicit saved destination disclosure
Authorized administrators SHALL be able to explicitly reveal the saved URL through
a permission-checked, non-cacheable read. Ordinary settings responses MUST remain
masked and the signing secret MUST NOT be disclosed. Hiding or leaving the editor
SHALL discard the revealed value without changing saved configuration.

#### Scenario: Reveal saved destination
- **WHEN** an authorized administrator requests the saved destination
- **THEN** only the URL is returned with Cache-Control no-store and the action is audited without its value

#### Scenario: Unauthorized disclosure
- **WHEN** a dashboard user without security-write permission requests the saved destination
- **THEN** access is denied
