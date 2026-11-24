## MODIFIED Requirements

### Requirement: Exhausted soft sticky owners are released
When a request resolves a `prompt_cache`, `sticky_thread` or soft `codex_session` mapping whose owner is not rate-limited and whose latest usage snapshot reports the primary or secondary window at 100 percent or more, selection MUST release the mapping and route to another account when the pool's best candidate is neither the owner nor itself exhausted, regardless of routing strategy and of the owner's routing policy. The same rule MUST apply to a session seed preference that would create a new mapping: a preferred account that is not rate-limited and reports an exhausted window MUST be declined when the pool's best candidate is neither that account nor itself exhausted, and the new mapping MUST then be created for the account normal selection chooses. The replacement MAY be above the sticky budget thresholds. When every candidate is exhausted the owner or preferred account MUST be kept. Usage evidence MUST follow the same priority and limit-scoped fields as the sticky budget thresholds. Hard continuity owners MUST NOT be released by this rule.

#### Scenario: Exhausted burn-first owner moves to a sibling with quota left
- **GIVEN** a `prompt_cache` mapping pinned to a burn-first account whose primary window reports 100%
- **AND** a normal account whose primary window reports 97%
- **WHEN** the next request on the mapping is selected
- **THEN** it is routed to the normal account and the mapping is rebound to it

#### Scenario: Exhausted owner is kept when the whole pool is exhausted
- **GIVEN** a soft mapping pinned to an account whose primary window reports 100%
- **AND** every other account reports a window at 100%
- **WHEN** the next request on the mapping is selected
- **THEN** the pinned account is kept

#### Scenario: Burn-first owner below exhaustion is held
- **GIVEN** a soft mapping pinned to a burn-first account at 99% primary usage, above the budget threshold
- **WHEN** the next request on the mapping is selected
- **THEN** the pinned account is kept

#### Scenario: New thread does not inherit an exhausted session account
- **GIVEN** a request for a thread without a mapping whose session prefers an account reporting its primary window at 100%
- **AND** another account whose windows are below 100%
- **WHEN** the request is selected
- **THEN** it is routed to the other account and the new mapping names that account

#### Scenario: Exhausted session preference is kept when the whole pool is exhausted
- **GIVEN** a request for a thread without a mapping whose session prefers an account reporting a window at 100%
- **AND** every other account reports a window at 100%
- **WHEN** the request is selected
- **THEN** the preferred account is selected
