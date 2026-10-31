## MODIFIED Requirements

### Requirement: Reconnect identity diagnostics
Credential import and OAuth reconnect SHALL distinguish a different authenticated
account, a different organization for the same verified account, and an identity
mismatch whose saved identity is unavailable for comparison. A mismatch SHALL NOT
change saved credentials, identity or ownership; it SHALL be answered with 409 and
the mismatch code, and the reconnect SHALL be held for confirmation. Logs SHALL
contain only the local source ID and mismatch category, excluding tokens,
provider UUIDs and profile contents.

#### Scenario: Same account with a different organization
- **WHEN** reconnect returns the saved account UUID but a different identity fingerprint
- **THEN** the dashboard returns 409 `claude_reconnect_organization_changed` and explains that the account matches but its organization differs

#### Scenario: Different authenticated account
- **WHEN** reconnect returns an account UUID different from the saved UUID
- **THEN** the dashboard returns 409 `claude_reconnect_account_mismatch`

#### Scenario: Legacy identity mismatch
- **WHEN** the saved account has no identity fingerprint or no account UUID and the incoming identity differs
- **THEN** the dashboard returns 409 `claude_reconnect_identity_unverified` without claiming either component matches

#### Scenario: Subscription change with stable identity
- **WHEN** reconnect supplies current credentials for the same account and organization after expiry and a subscription change
- **THEN** reconnect succeeds without confirmation and without requiring the previous subscription tier

### Requirement: Explicit credential identity replacement
Operators SHALL replace the authenticated Claude identity of an existing account
entry by confirming a held reconnect. A mismatched reconnect SHALL be held for ten
minutes with its credentials encrypted, bound to the account and the credential
generation it was started against. The mismatch response SHALL carry the pending ID,
its expiry and a comparison of the saved and incoming email, organization name and
plan. `POST /api/claude-accounts/{id}/pending-reconnects/{pending_id}/confirm` SHALL
replace the identity with the held credentials;
`DELETE /api/claude-accounts/{id}/pending-reconnects/{pending_id}` SHALL discard
them. A pending reconnect SHALL be usable once, and an expired, unknown or stale one
SHALL be rejected without changes. Replacement SHALL preserve settings, account ID,
historical accounting and the discovered model catalog; it SHALL reset current
subscription/quota observations, cooldowns and native resource ownership, and SHALL
mark the catalog due for rediscovery. Replacement SHALL advance credential
generation and the retained identity generation atomically. A request whose account
identity is replaced during preparation or before sending SHALL NOT dispatch:
resource-bound continuations SHALL return their resource error, including replayable
`thread_not_found` for native threads, and other requests SHALL return retryable
503 `claude_identity_changed` with `Retry-After: 1`. Claude accounts SHALL store
the email and organization name of their last authenticated profile and expose them
in account responses.

#### Scenario: Reauthorize a changed identity
- **WHEN** fresh OAuth or imported credentials authenticate a different identity and the operator confirms the pending reconnect
- **THEN** the selected entry receives the held credentials while its settings and historical accounting remain intact

#### Scenario: Discard a changed identity
- **WHEN** the operator discards the pending reconnect, or it expires
- **THEN** the saved credentials stay unchanged and the pending ID can no longer be confirmed

#### Scenario: Routable during rediscovery
- **WHEN** an identity is replaced before the next catalog refresh
- **THEN** selected models remain routable for the new identity and the scheduler rediscovers the catalog

#### Scenario: Stale OAuth completion
- **WHEN** the account generation changed after a reconnect flow started
- **THEN** completion cannot replace credentials or clear ownership/state

#### Scenario: Stale confirmation
- **WHEN** the account generation changed after a reconnect was held
- **THEN** confirming it fails without replacing credentials

#### Scenario: Old provider state
- **WHEN** history contains search state issued before identity replacement
- **THEN** completed search history is projected to readable content and active server-bound history is rejected before dispatch

#### Scenario: Replacement during preparation
- **WHEN** replacement commits after a request selected the account but before dispatch
- **THEN** a native thread continuation receives thread_not_found and an ordinary request receives retryable claude_identity_changed, without an upstream send

#### Scenario: Late upstream response
- **WHEN** a request from the old identity finishes after replacement
- **THEN** its provenance and quota observations cannot become current for the new identity

#### Scenario: Unchanged identity
- **WHEN** a reconnect authenticates the saved identity
- **THEN** it completes immediately, preserves continuation ownership and follows ordinary credential rotation
