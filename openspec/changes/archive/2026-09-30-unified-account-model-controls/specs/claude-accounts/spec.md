## MODIFIED Requirements

### Requirement: Selected catalog and pooled routing
Explicitly selected available models, or all discovered models with resolved capabilities when All models is enabled, on enabled, credential-healthy and client-authorized accounts SHALL be routed. Selected mode SHALL be the default and synchronization MUST preserve curated choices across mode switches. Catalog synchronization MUST paginate atomically and retain the previous snapshot on failure. Quota monitoring SHALL represent observed shared and model-specific windows and unknown/stale state truthfully. Pool attempts MUST preserve model, opaque-state ownership, admission and exactly-once settlement; no retry SHALL occur after visible output or ambiguous dispatch.

#### Scenario: Automatic Claude catalog
- **WHEN** All models is enabled and discovery adds a model with resolved limits
- **THEN** it becomes available while unavailable models remain disabled and curated selections are retained

#### Scenario: Model-specific exhaustion
- **WHEN** an account has an exhausted model-specific window
- **THEN** that account is ineligible for that model without disabling unrelated models

#### Scenario: Unavailable continuation owner
- **WHEN** account-bound continuation names a paused, unauthorized, refreshing or quota-exhausted owner
- **THEN** selection returns an explicit owner-unavailable error without choosing another account

#### Scenario: Worker-independent affinity
- **WHEN** separate workers evaluate an admitted conversation with the same client scope and model and an eligible retained owner
- **THEN** account selection honors its durable affinity regardless of database row order

#### Scenario: Missing quota and entitlement information
- **WHEN** quota monitoring omits a window or returns null
- **THEN** the dashboard represents it as unknown, not zero usage or a denied model entitlement

#### Scenario: Stale exhausted quota
- **WHEN** an exhausted window has a future reset but monitoring has become stale
- **THEN** its known exhaustion continues to block applicable models until reset or a newer observation
- **AND** passing its reset changes the observation to unknown rather than fabricating zero usage
