## MODIFIED Requirements

### Requirement: Selected catalog and pooled routing
Only explicitly selected available models on enabled, credential-healthy and client-authorized accounts SHALL be routed. Catalog synchronization MUST paginate atomically and retain the previous snapshot on failure. Quota monitoring SHALL represent observed shared and model-specific windows and unknown/stale state truthfully. Pool attempts MUST preserve model, opaque-state ownership, admission and exactly-once settlement; no retry SHALL occur after visible output or ambiguous dispatch.

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

## ADDED Requirements

### Requirement: Shared Claude routing policy
Claude SHALL use the dashboard routing strategy, earlier-reset preference and
relative-availability tuning through the shared strategy implementation. Claude
SHALL supply normalized equal account capacities, never OpenAI plan estimates.
Fresh five-hour usage SHALL map to primary; fresh applicable weekly pressure
SHALL map to secondary. Unknown/stale ranking data SHALL follow an explicit
neutral policy, not be represented as observed zero usage.
Authorization, quota exclusion, hard ownership and eligible affinity SHALL remain
enforced. Single-account mode SHALL use a distinct Claude target and fail closed
when missing, unavailable or conflicting with resource ownership. Successful
source admission SHALL update Claude selection recency.

#### Scenario: Earlier-reset policy
- **WHEN** an unbound Claude request uses reset-drain
- **THEN** eligible normalized candidates follow the same reset-drain ordering as Codex

#### Scenario: Provider-specific single account
- **WHEN** single-account mode selects an OpenAI target but no Claude target
- **THEN** Claude fails explicitly without using the OpenAI account or guessing a Claude target

#### Scenario: Bound conversation
- **WHEN** quota ranking favors another account but an eligible hard owner is required
- **THEN** the hard owner remains selected
