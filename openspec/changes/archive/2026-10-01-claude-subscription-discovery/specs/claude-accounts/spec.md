## ADDED Requirements

### Requirement: Automatic Claude subscription discovery
Explicit credential imports SHALL preserve non-secret subscriptionType and
rateLimitTier. Account responses SHALL expose a derived Free, Pro, Max, Max 5x,
Max 20x, Team, Enterprise or Unknown plan. Known specific rate-limit tiers SHALL
take priority over generic subscription type. Absent or unsupported identifiers
MUST NOT imply Free, Max 20x, quota capacity or model entitlement.

#### Scenario: Imported Max multiplier
- **WHEN** an imported credential reports subscriptionType max and rateLimitTier default_claude_max_5x
- **THEN** the account displays Max 5x without changing routing or quota limits

### Requirement: Coordinated subscription metadata refresh
The gateway SHALL read /api/claude_cli/bootstrap with its maintained Claude CLI
management headers and validate the authenticated account and organization.
Subscription polling SHALL use independent durable claims, six-hour successful
cadence, generation fencing and existing metadata Retry-After cooldowns. Manual
refresh MUST NOT bypass cooldowns or claims. Existing accounts SHALL participate
without reimport. Failures SHALL retain last-known subscription metadata and
timestamps and expose a safe diagnostic without changing inference health.

#### Scenario: Account upgrade
- **WHEN** authenticated bootstrap changes an imported Pro subscription to Max 20x
- **THEN** the retained metadata and displayed plan become Max 20x

#### Scenario: Failed discovery
- **WHEN** bootstrap returns 429 or malformed metadata
- **THEN** last-known metadata is retained and cooldown applies independently of catalog and usage

#### Scenario: Identity or generation mismatch
- **WHEN** bootstrap identifies another account or the credential generation changes during its fetch
- **THEN** the response cannot overwrite the enrolled account's subscription

### Requirement: Claude plan presentation
Claude cards, account lists and details SHALL show localized plan labels in
existing account subtitle styling. Provider labels SHALL say Claude, without an
OAuth suffix; authentication-method controls SHALL remain distinct. Account search SHALL match the detected plan.
Unknown data SHALL remain explicit; detail diagnostics SHALL identify failed
subscription refreshes without exposing tokens or raw upstream bodies.

#### Scenario: Unknown subscription
- **WHEN** an account has no recognized subscription metadata
- **THEN** the account subtitle shows an unknown plan rather than a guessed tier

### Requirement: Claude request plan snapshots
Claude native Messages, token counts, translated Responses and Chat requests SHALL
record the selected account's normalized subscription at dispatch preparation.
Successful and failed attempts SHALL retain that snapshot through settlement,
including downstream WebSocket requests and account failover. Request tables and
details SHALL display the same localized plan labels as accounts. Historical
rows lacking a snapshot MUST NOT be relabeled using current account metadata.

#### Scenario: Subscription changes during inference
- **WHEN** a Pro account becomes Max 20x while a prepared request is running
- **THEN** that request log still shows Pro and subsequent preparations show Max 20x

#### Scenario: No known subscription
- **WHEN** a Claude request is prepared without recognized subscription metadata
- **THEN** its log records Unknown, distinct from historical rows without a plan
