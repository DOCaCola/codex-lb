# client-usage-reporting Specification

## Purpose
TBD - created by archiving change report-pool-usage-to-codex-clients. Update Purpose after archive.

## Requirements

### Requirement: Client pool usage reflects routable capacity

Usage reported to Codex clients for a provider pool SHALL be computed over that provider's non-paused, non-deactivated
accounts, weighted by each account's plan capacity for the window. An account that reports no window of a given
duration SHALL count as 0% used in that window with its plan's capacity, unless it is exhausted. An account whose latest
snapshot reports any applicable window at 100% SHALL count as 100% used in every window. A window's reset time SHALL
be the earliest reset among accounts with more than 0% usage in that window, and SHALL be omitted when there is none.
A snapshot whose reset time has elapsed SHALL NOT count as reporting its window, and a window SHALL be reported only when
some account reports it. When no account has a known plan capacity for a window, accounts SHALL weigh equally.

#### Scenario: Accounts without a 5h window do not make the pool 5h-limited

- **GIVEN** two Pro accounts reporting only a weekly window below 100%
- **AND** a Plus account reporting its 5h window at 100% and its weekly window below 100%
- **WHEN** the OpenAI pool usage is computed for a client
- **THEN** the 5h figure is the capacity-weighted share of the Plus account's usage, not 100%
- **AND** the 5h reset time is the Plus account's 5h reset

#### Scenario: An exhausted account counts as fully used

- **GIVEN** an account without a 5h window whose weekly window is at 100%
- **WHEN** the pool usage is computed for a client
- **THEN** that account counts as 100% used in both windows

#### Scenario: Idle accounts do not set the reset time

- **GIVEN** an account at 0% in a window with a reset earlier than every account with usage
- **WHEN** the pool usage is computed for a client
- **THEN** the reported reset time is the earliest reset of an account with usage

#### Scenario: An elapsed window is no longer reported

- **GIVEN** the only 5h snapshot in the pool has a reset time in the past
- **WHEN** the pool usage is computed for a client
- **THEN** no 5h window is reported
- **AND** that snapshot does not mark its account exhausted

### Requirement: Claude pool usage uses plan units and the served model's weekly limit

The Claude pool SHALL weight accounts by plan units (Pro 1, Max 5x 5, Max 20x 20) and report the `five_hour` window
and a weekly window. For each account, the weekly figure SHALL be the most-used weekly window applicable to the served
model, including `seven_day_opus` or `seven_day_sonnet` where they apply, with that window's reset.

#### Scenario: Model-specific weekly limit binds

- **GIVEN** a Claude account with `seven_day` at 40% and `seven_day_opus` at 90%
- **WHEN** the Claude pool usage is computed for an Opus turn
- **THEN** that account contributes 90% to the weekly figure

### Requirement: Native Codex clients receive the serving provider's pool usage

On native Codex routes and on every Responses WebSocket route, every `codex.rate_limits` event and every set of
`x-codex-*` usage headers sent to the client
SHALL describe the pool of the provider that served the turn: the OpenAI pool for OpenAI accounts and the Claude pool
for Claude accounts. Turns served by OpenRouter or OpenAI-compatible model sources SHALL carry neither event nor
headers. An upstream `codex.rate_limits` event SHALL be replaced by the pool snapshot and SHALL NOT be merged with it;
an event for another limit family SHALL be replaced by that family's pool aggregate, or dropped when the pool has none.
When `hide_upstream_quota_from_api_keys` applies to the client, the event SHALL be dropped. Live usage ingestion SHALL
read the upstream event before it is replaced. A turn served by a Claude account SHALL emit one `codex.rate_limits`
event before its terminal event on WebSocket routes.

#### Scenario: Selected account usage is not exposed

- **GIVEN** a WebSocket turn served by an OpenAI account whose upstream event reports its 5h window at 100%
- **WHEN** the event is forwarded to a native Codex client
- **THEN** the client receives the OpenAI pool snapshot
- **AND** live usage ingestion records 100% for that account

#### Scenario: Claude turn reports the Claude pool

- **GIVEN** every OpenAI account is exhausted and Claude accounts have quota left
- **WHEN** a native Codex client completes a turn on a Claude model
- **THEN** the usage it receives is the Claude pool's

#### Scenario: OpenRouter turn reports nothing

- **WHEN** a native Codex client completes a turn served by an OpenRouter account
- **THEN** the turn carries no `codex.rate_limits` event and no `x-codex-*` usage headers

#### Scenario: Hidden quota drops the event

- **GIVEN** `hide_upstream_quota_from_api_keys` is enabled
- **WHEN** an API-key client receives a WebSocket turn
- **THEN** the stream contains no `codex.rate_limits` event

### Requirement: Codex usage endpoint lists every subscription pool

`/api/codex/usage` for a caller that does not resolve to a codex-lb API key SHALL report the OpenAI pool as its
primary rate limit, computed as in "Client pool usage reflects routable capacity", and SHALL include the Claude pool as
an additional rate limit with `limit_name` `Claude` and `metered_feature` `claude` when Claude accounts are active.

#### Scenario: Status lists both pools

- **GIVEN** active OpenAI and Claude accounts
- **WHEN** a ChatGPT-authenticated client requests `/api/codex/usage`
- **THEN** the payload's rate limit is the OpenAI pool
- **AND** its additional rate limits include `claude` with the Claude pool's 5h and weekly windows
