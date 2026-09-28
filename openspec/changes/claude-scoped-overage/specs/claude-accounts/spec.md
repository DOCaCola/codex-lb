## ADDED Requirements

### Requirement: Scoped Claude overage restrictions
Claude 429 recovery SHALL distinguish shared subscription rejection from requested-model overage or entitlement rejection. Healthy shared windows with explicit overage-only evidence SHALL NOT create an account-wide restriction. An omitted shared-window status SHALL require finite nonnegative utilization below one and another explicitly allowed shared window to establish health; missing or malformed usage MUST NOT imply health. Explicit shared rejection SHALL retain account-wide scope. Structured credits_required errors SHALL restrict the requested model without suppressing independently rejected shared windows. Fast-mode entitlement refusals SHALL retain existing no-failover behavior.

Mixed shared and model rejection SHALL preserve both restrictions atomically with independently attributable deadlines. Model-specific Retry-After or reset MUST NOT extend shared cooldowns. Aggregate deadlines SHALL apply only to an identified scope or the sole unambiguous scope; otherwise the existing default SHALL apply. Existing longer restrictions MUST NOT be shortened or cleared. Restrictions MUST NOT infer additional affected models from a model-family name. Authorization, hard ownership, settlement ordering and physical-send budgets SHALL remain unchanged across native Messages, count_tokens and Responses HTTP/WebSocket paths.

#### Scenario: Overage-only refusal
- **WHEN** a model is rejected for overage while shared subscription windows are healthy
- **THEN** that model is restricted but sibling models remain selectable on the same account

#### Scenario: Model-window overshoot
- **WHEN** a 429 reports finite model-window utilization at or above one while shared windows are healthy
- **THEN** the requested model is restricted using its window deadline even if its status header is absent

#### Scenario: Mixed rejection
- **WHEN** a shared window resets in two hours and a model window resets in eighty hours
- **THEN** both restrictions persist and after two hours only the affected model remains restricted

#### Scenario: Ambiguous unified rejection
- **WHEN** unified status is rejected without enough evidence to isolate an overage-only failure
- **THEN** account-wide protection is retained and missing usage is not interpreted as healthy

## MODIFIED Requirements

### Requirement: Reactive Claude quota failover
The gateway SHALL classify upstream 429 refusals before health mutation. Fast-mode credit entitlement refusals SHALL NOT cool the pool. Shared or ambiguous unified quota rejection SHALL cool the account; proven overage-only and ordinary model limits SHALL cool only the requested model. Each restriction SHALL use only its attributable deadlines: a valid Retry-After SHALL be a minimum wait alongside explicit rejected-window resets, then an attributable aggregate reset when window resets are unavailable, then a 60-second default. Deadlines SHALL persist and never shorten on concurrent writes. The gateway MAY select another authorized eligible account before output, excluding failed accounts, and MUST rebuild identity, credentials and history projection for that target. Active reasoning and server-resource ownership MUST remain enforced. A logical request SHALL permit at most four physical sends including signature recovery. Canceled requests and errors after stream ownership SHALL NOT trigger account failover. Every failed attempt SHALL settle and release admission before another attempt; exhausted recovery SHALL preserve the last upstream refusal.

#### Scenario: Alternate succeeds
- **WHEN** account A returns a retryable 429 and account B is eligible
- **THEN** B receives a freshly prepared request after A settles

#### Scenario: Entitlement refusal
- **WHEN** upstream refuses fast mode for missing credits
- **THEN** the refusal is returned without cooling ordinary account traffic

#### Scenario: Bounded recovery
- **WHEN** all selected accounts refuse or signature recovery consumes the send budget
- **THEN** no more than four physical sends occur

#### Scenario: Owned history
- **WHEN** active reasoning or server resources prevent account migration
- **THEN** the original refusal is returned without sending to another owner
