## ADDED Requirements

### Requirement: Operators can refresh a Codex account without a model request

The dashboard MUST expose `POST /api/accounts/{account_id}/refresh`, requiring account write permission, that forces an immediate usage refresh of one account through the scheduled-refresh usage updater, regardless of usage freshness, and MUST NOT send a model request. The account-selection cache MUST be invalidated after every forced attempt, because the refresh can persist renewed credentials before a failed fetch.

#### Scenario: Refresh of a paused account
- **GIVEN** a paused Codex account
- **WHEN** an operator POSTs to `/api/accounts/{account_id}/refresh`
- **THEN** the account's usage is fetched from upstream and stored
- **AND** no model request is sent

#### Scenario: Refresh of an account that needs re-authentication
- **WHEN** an operator POSTs to `/api/accounts/{account_id}/refresh` for a `reauth_required` or `deactivated` account
- **THEN** the endpoint responds `409` with code `account_not_refreshable`

#### Scenario: Upstream usage fetch fails
- **WHEN** the forced usage fetch does not complete
- **THEN** the endpoint responds `502` with code `account_usage_refresh_failed`
- **AND** the account-selection cache is invalidated

## MODIFIED Requirements

### Requirement: Operators can probe an account to wake the upstream limiter

The dashboard MUST expose an admin-only endpoint that sends a single minimal `responses.create` directly to upstream pinned to one account, bypassing load-balancer scoring, then immediately refreshes that account's `/wham/usage` snapshot. The probe request MUST omit `max_output_tokens`: it closes the stream after response headers, so an output limit would bound nothing. The endpoint MUST surface the before/after usage and account status so operators can verify whether the upstream limiter re-evaluated.

#### Scenario: Probe wakes the upstream limiter and refreshes usage state
- **WHEN** an operator POSTs to `/api/accounts/{account_id}/probe`
- **AND** the account is `active`, `rate_limited`, or `quota_exceeded`
- **THEN** the service sends one `responses.create` request directly to `{upstream_base_url}/codex/responses` with `stream=true`, `store=false`, and no `max_output_tokens` field
- **AND** the service triggers an immediate `UsageUpdater.refresh_accounts` for that account
- **AND** the response body carries `probe_status_code`, `primary_used_percent_before`, `primary_used_percent_after`, `secondary_used_percent_before`, `secondary_used_percent_after`, `account_status_before`, `account_status_after`

#### Scenario: Probe rejects hard-blocked accounts
- **WHEN** an operator POSTs to `/api/accounts/{account_id}/probe`
- **AND** the account `status` is `paused` or `deactivated`
- **THEN** the endpoint responds `409` with code `account_not_probable`
- **AND** no upstream request is sent

#### Scenario: Dashboard exposes Force probe only for probeable statuses

- **WHEN** the dashboard renders the Codex account's "More actions" menu
- **AND** the account `status` is `active`, `rate_limited`, or `quota_exceeded`
- **THEN** the menu offers a Force probe item for that account
- **AND** invoking the item refreshes the account list, dashboard overview, projections, and that account's trends
- **BUT WHEN** the account `status` is `paused` or `deactivated`
- **THEN** the Force probe item is disabled

#### Scenario: Probe returns 404 for unknown account
- **WHEN** an operator POSTs to `/api/accounts/{account_id}/probe`
- **AND** no account with that id exists
- **THEN** the endpoint responds `404` with code `account_not_found`
