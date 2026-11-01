## MODIFIED Requirements

### Requirement: Coordinated Claude metadata refresh
Usage and catalog refreshes SHALL coordinate independently through durable per-account endpoint claims and cooldowns. Scheduled usage refresh SHALL run no more often than every three minutes and catalog refresh every six hours. Manual refresh MAY bypass successful-cache cadence and the cooldown after a failed attempt that was not rate limited, but MUST NOT bypass an active claim or a 429 rate-limit cooldown. Claims SHALL expire after bounded execution and completion SHALL require the owning claim and credential generation. Network I/O MUST NOT hold database write locks, and the metadata fetch timeout SHALL bound only network I/O; database work, including the subscription identity check, SHALL run outside it.

Last successful observations and timestamps SHALL survive failures. HTTP errors SHALL identify the metadata endpoint without exposing response bodies or credentials. Valid Retry-After seconds or HTTP dates SHALL establish the next attempt time; absent or invalid hints SHALL use three minutes. Failure on one endpoint MUST NOT prevent refreshing the other. Metadata failures MUST NOT pause accounts, penalize inference health, or trigger reactive credential rotation. Fresh inference quota headers SHALL retain their independent authority.

#### Scenario: Rate-limited usage
- **WHEN** usage returns 429 with Retry-After
- **THEN** manual and scheduled refreshes return retained state until that deadline without another usage request, including after worker restart

#### Scenario: Manual refresh after a failure that was not rate limited
- **WHEN** usage failed with malformed data or a non-429 error and its cooldown is still active
- **THEN** a scheduled refresh waits, and a manual refresh sends immediately unless a claim is active

#### Scenario: Concurrent refresh
- **WHEN** two workers refresh the same endpoint
- **THEN** only the durable claim owner sends and a late or replaced-generation completion cannot overwrite state

#### Scenario: Endpoint isolation
- **WHEN** catalog is cooling down but usage is due
- **THEN** usage still refreshes and catalog retains its last successful data

#### Scenario: Slow identity check
- **WHEN** the subscription identity check's database read outlasts the metadata fetch timeout
- **THEN** the subscription refresh still completes and the refresh's state write succeeds

### Requirement: Coordinated subscription metadata refresh
The gateway SHALL read /api/claude_cli/bootstrap with its maintained Claude CLI
management headers and validate the authenticated account and organization.
Subscription polling SHALL use independent durable claims, six-hour successful
cadence, generation fencing and existing metadata Retry-After cooldowns. Manual
refresh MUST NOT bypass claims or 429 rate-limit cooldowns, and SHALL bypass the
cooldown after other failures. Existing accounts SHALL participate
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
