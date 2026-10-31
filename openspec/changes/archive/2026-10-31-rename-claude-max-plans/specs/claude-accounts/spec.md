## MODIFIED Requirements

### Requirement: Automatic Claude subscription discovery
Explicit credential imports SHALL preserve non-secret subscriptionType and
rateLimitTier. Account responses SHALL expose a derived Free, Pro, Max, Ultra,
Team, Enterprise or Unknown plan. Rate-limit tiers SHALL take priority over
subscription type. The tiers `max_5x` and `max` SHALL resolve to Max, and
`max_20x` and `ultra` SHALL resolve to Ultra, with or without the
`default_claude_` prefix. A subscription type of `max` alone SHALL NOT
resolve to a plan, because it named both tiers before Anthropic's 2026-10-30
rename. Absent or unsupported identifiers MUST NOT imply Free, Ultra, quota
capacity or model entitlement.

#### Scenario: Imported Max multiplier
- **WHEN** an imported credential reports subscriptionType max and rateLimitTier default_claude_max_5x
- **THEN** the account displays Max without changing routing or quota limits

#### Scenario: Former Max 20x tier
- **WHEN** metadata reports rateLimitTier default_claude_max_20x
- **THEN** the account displays Ultra

#### Scenario: Generic Max subscription without a tier
- **WHEN** metadata reports subscriptionType max and no rate-limit tier
- **THEN** the account displays an unknown plan rather than Max or Ultra

### Requirement: Coordinated subscription metadata refresh
The gateway SHALL read /api/claude_cli/bootstrap with its maintained Claude CLI
management headers and validate the authenticated account and organization.
Subscription polling SHALL use independent durable claims, six-hour successful
cadence, generation fencing and existing metadata Retry-After cooldowns. Manual
refresh MUST NOT bypass cooldowns or claims. Existing accounts SHALL participate
without reimport. Failures SHALL retain last-known subscription metadata and
timestamps and expose a safe diagnostic without changing inference health.

#### Scenario: Account upgrade
- **WHEN** authenticated bootstrap changes an imported Pro subscription to Ultra
- **THEN** the retained metadata and displayed plan become Ultra

#### Scenario: Failed discovery
- **WHEN** bootstrap returns 429 or malformed metadata
- **THEN** last-known metadata is retained and cooldown applies independently of catalog and usage

#### Scenario: Identity or generation mismatch
- **WHEN** bootstrap identifies another account or the credential generation changes during its fetch
- **THEN** the response cannot overwrite the enrolled account's subscription

### Requirement: Claude request plan snapshots
Claude native Messages, token counts, translated Responses and Chat requests SHALL
record the selected account's normalized subscription at dispatch preparation.
Successful and failed attempts SHALL retain that snapshot through settlement,
including downstream WebSocket requests and account failover. Request tables and
details SHALL display the same localized plan labels as accounts. Historical
rows lacking a snapshot MUST NOT be relabeled using current account metadata.
Snapshots recorded under the former keys `max_5x` and `max_20x` SHALL be
renamed to `max` and `ultra`, keeping the plan recorded at dispatch.

#### Scenario: Subscription changes during inference
- **WHEN** a Pro account becomes Ultra while a prepared request is running
- **THEN** that request log still shows Pro and subsequent preparations show Ultra

#### Scenario: No known subscription
- **WHEN** a Claude request is prepared without recognized subscription metadata
- **THEN** its log records Unknown, distinct from historical rows without a plan

#### Scenario: Snapshot recorded before the rename
- **WHEN** a request log recorded `max_20x` before the rename
- **THEN** it displays Ultra

## ADDED Requirements

### Requirement: Claude plan weights per window
Pooled Claude figures SHALL weight each account in Pro units per quota window:
five-hour Pro 1, Max 5 and Ultra 20; weekly Pro 1, Max 5 and Ultra 10, matching
Anthropic's published limits. Weekly figures include model-scoped weekly
windows. Account responses SHALL expose both weights; plans without a published
multiplier have none and are not pooled.

#### Scenario: Ultra weekly capacity
- **WHEN** the Claude weekly pace pools a Pro and an Ultra account
- **THEN** their combined weekly capacity is 11 Pro units

#### Scenario: Ultra five-hour capacity
- **WHEN** an unverified Ultra account reports a five-hour window
- **THEN** that window contributes 20 Pro units to the pooled five-hour figure
