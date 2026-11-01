## MODIFIED Requirements

### Requirement: Coordinated Claude metadata refresh
Usage and catalog refreshes SHALL coordinate independently through durable per-account endpoint claims and cooldowns. Inference reply headers SHALL be the primary quota source: scheduled usage refresh SHALL run only when neither the last successful usage response nor any five-hour or weekly header observation is newer than 15 minutes, or when the last successful usage response is at least one hour old. Catalog refresh SHALL run every six hours. Manual refresh MAY bypass successful-cache cadence and the cooldown after a failed attempt that was not rate limited, but MUST NOT bypass an active claim or a 429 rate-limit cooldown of the current credential generation. Claims SHALL expire after bounded execution and completion SHALL require the owning claim and credential generation. Network I/O MUST NOT hold database write locks, and the metadata fetch timeout SHALL bound only network I/O; database work, including the subscription identity check, SHALL run outside it.

Last successful observations and timestamps SHALL survive failures. HTTP errors SHALL identify the metadata endpoint without exposing response bodies or credentials. Valid Retry-After seconds or HTTP dates SHALL establish the next attempt time; absent or invalid hints SHALL use five minutes. A 429 cooldown SHALL bind the credential generation that received it; after a credential refresh the endpoint SHALL follow its normal cadence. Failure on one endpoint MUST NOT prevent refreshing the other. Metadata failures MUST NOT pause accounts, penalize inference health, or trigger reactive credential rotation. Fresh inference quota headers SHALL retain their independent authority.

#### Scenario: Busy account
- **WHEN** inference replies keep five-hour and weekly header observations newer than 15 minutes and the last usage response is under an hour old
- **THEN** scheduled refresh sends no usage request

#### Scenario: Idle account
- **WHEN** no header observation or usage response is newer than 15 minutes
- **THEN** the next scheduled refresh reads usage

#### Scenario: Endpoint-only data ages
- **WHEN** headers are fresh but the last successful usage response is an hour old
- **THEN** the next scheduled refresh reads usage

#### Scenario: Rate-limited usage
- **WHEN** usage returns 429 with Retry-After
- **THEN** manual and scheduled refreshes with the same credential generation return retained state until that deadline without another usage request, including after worker restart

#### Scenario: Refreshed credential after a rate limit
- **WHEN** usage returned 429 and the access token was refreshed before the Retry-After deadline
- **THEN** usage may be read again once its cadence is due

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

### Requirement: Live Claude quota observation
The gateway SHALL observe valid five-hour (`5h`), seven-day (`7d`) and model-scoped seven-day (`7d_oi`) utilization headers on physical Claude HTTP responses, including rejected attempts, before retry or stream completion. It SHALL also observe whether `anthropic-ratelimit-unified-overage-in-use` reports extra usage in use. Observations SHALL be attributed to the sending source and credential generation; stale-generation or deleted-account observations MUST NOT persist. Finite nonnegative header fractions SHALL become percentages, including values above 100%; malformed, negative or nonfinite converted values SHALL leave prior evidence unchanged. The gateway MUST NOT guess alternative scales or clamp stored utilization. Missing/reset-only headers MUST NOT invent usage or extend retained usage.

Window freshness and provenance SHALL distinguish header receipt from polling. Evidence SHALL remain fresh for 30 minutes after observation, two idle usage-refresh intervals, unless the poll that produced it later failed. Header updates MUST NOT mark unrelated windows fresh, clear poll errors, erase model-specific windows or clear refusal cooldowns. Request-start ordering SHALL prevent older concurrent requests from replacing newer observations; expired evidence SHALL be unknown. Atomic bounded merges SHALL preserve concurrent settings/catalog updates. History SHALL record every sample whose utilization or reset deadline differs from the latest stored sample for that account/window; unchanged samples SHALL be bounded to one per account/window/minute. Observation failures MUST NOT fail or retry inference; cancellation and upstream ownership SHALL remain intact.

The observation write SHALL run inline to completion without its own timeout. Caller cancellation during the write SHALL be delivered after the write finishes.

#### Scenario: Failover attribution
- **WHEN** account A returns quota headers with 429 before account B succeeds
- **THEN** both observations belong to their respective sending accounts

#### Scenario: Partial observation
- **WHEN** headers contain only five-hour utilization
- **THEN** other windows retain their previous evidence and freshness

#### Scenario: Model-scoped observation
- **WHEN** a reply carries `7d_oi` utilization 0.42
- **THEN** the Weekly Fable window reports 42% from inference headers

#### Scenario: Idle account between reads
- **WHEN** an account's last evidence is 20 minutes old and no poll failed
- **THEN** its windows are fresh and the account remains eligible for quota-ranked routing

#### Scenario: Replaced credentials
- **WHEN** a physical response arrives after its sending credential generation was replaced
- **THEN** its quota observation is discarded

#### Scenario: Utilization overshoot
- **WHEN** a fresh five-hour utilization header contains 1.04
- **THEN** persisted usage and dashboard text report 104%, the window is exhausted, and remaining-quota bar width is zero

#### Scenario: Exhaustion within the sampling minute
- **WHEN** five-hour utilization moves from 99% to 100% 27 seconds after the 99% sample with the same reset deadline
- **THEN** history stores the 100% sample
- **AND** a repeated 100% sample within the same minute is not stored

#### Scenario: Slow observation write
- **WHEN** persisting an observation takes longer than under normal load
- **THEN** the observation is recorded and the write is not cancelled

#### Scenario: Cancelled during observation
- **WHEN** the request is cancelled while its observation is being written
- **THEN** the write completes before the cancellation propagates

### Requirement: Optional model-specific quota presentation
Claude quota responses SHALL omit null Opus/Sonnet weekly windows when a successful retained usage snapshot establishes they were not reported. The Weekly Fable window SHALL combine the usage response's `weekly_scoped` limit whose model scope is named Fable with `7d_oi` header observations, newest request first, and SHALL be shown only once either source reported it. Fable models SHALL be subject to it like Opus and Sonnet models to their windows. Shared windows SHALL retain unknown states when unavailable. Before any successful usage snapshot, Opus/Sonnet windows MAY remain unknown. Known scoped observations SHALL remain visible under stale, expired or reset-barrier states. Missing scoped windows MUST NOT imply model unavailability, unlimited entitlement or shared-quota duplication.

#### Scenario: Pro account without scoped windows
- **WHEN** a successful usage response includes shared windows and null model-specific windows
- **THEN** account details show the shared limits without unknown Opus/Sonnet quota rows

#### Scenario: Previously reported scoped quota is stale
- **WHEN** a scoped observation exists but a subsequent refresh fails
- **THEN** that observation remains visible as stale rather than disappearing

#### Scenario: Fable weekly window
- **WHEN** the usage response lists a Fable `weekly_scoped` limit at 30% or a later reply reports `7d_oi` utilization
- **THEN** account details show Weekly Fable from the newer source and an exhausted window blocks Fable models only

### Requirement: Claude extra usage presentation
Claude cards and account-list rows SHALL show a warning badge, in existing badge styling, when Anthropic usage data reports extra usage as enabled, or when a reply requested after the last usage read reports extra usage in use. The badge SHALL be absent when extra usage is disabled or unreported. A reply that does not report extra usage in use MUST NOT clear an enabled state reported by usage data.

#### Scenario: Extra usage enabled
- **WHEN** the latest usage data reports extra usage enabled for an account
- **THEN** its card and list row show an extra-usage badge explaining that requests beyond subscription limits are billed

#### Scenario: Extra usage billed between usage reads
- **WHEN** a reply newer than the last usage read carries `anthropic-ratelimit-unified-overage-in-use: true`
- **THEN** the account shows the extra-usage badge before the next usage read
