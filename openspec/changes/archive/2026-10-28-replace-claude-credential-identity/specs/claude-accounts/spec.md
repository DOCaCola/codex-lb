## MODIFIED Requirements

### Requirement: Explicit encrypted credential enrollment
Operators SHALL enroll Claude accounts through expiring single-use PKCE authorization or explicit Claude Code credential-file import. Credentials MUST be encrypted at rest, excluded from dashboard output and logs, and never read implicitly from server-local files. Imported expiry MUST be interpreted as milliseconds and validated. Enrollment MUST warn against concurrent refresh consumers.

#### Scenario: Invalid imported expiry
- **WHEN** a credentials file has missing, invalid or second-based expiresAt
- **THEN** enrollment fails explicitly without creating a usable account

#### Scenario: Reconnect to a different account
- **WHEN** replacement credentials authenticate a different account or organization without explicit identity replacement consent
- **THEN** reconnect fails without replacing credentials or retained ownership

#### Scenario: Refresh races reconnect
- **WHEN** a reconnect replaces credentials while an older refresh attempt remains in flight
- **THEN** the old generation cannot overwrite the replacement credentials

#### Scenario: Duplicate rotated grant
- **WHEN** a different current grant authenticates an already enrolled account and organization
- **THEN** enrollment rejects the duplicate using authenticated identity rather than the access token or display name

### Requirement: Reconnect identity diagnostics
Without explicit identity replacement consent, credential import and OAuth reconnect SHALL distinguish a different authenticated
account, a different organization for the same verified account, and an identity
mismatch whose saved account UUID is unavailable. Rejections SHALL preserve saved
credentials, identity and ownership. Logs SHALL contain only the local source ID
and mismatch category, excluding tokens, provider UUIDs and profile contents.

#### Scenario: Same account with a different organization
- **WHEN** reconnect returns the saved account UUID but a different identity fingerprint
- **THEN** the dashboard returns `claude_reconnect_organization_changed` and explains that the account matches but its organization differs

#### Scenario: Different authenticated account
- **WHEN** reconnect returns an account UUID different from the saved UUID
- **THEN** the dashboard returns `claude_reconnect_account_mismatch`

#### Scenario: Legacy identity mismatch
- **WHEN** the identity fingerprint differs and no account UUID was saved
- **THEN** the dashboard returns `claude_reconnect_identity_unverified` without claiming either component matches

#### Scenario: Subscription change with stable identity
- **WHEN** reconnect supplies current credentials for the same account and organization after expiry and a subscription change
- **THEN** reconnect succeeds without requiring the previous subscription tier

## ADDED Requirements

### Requirement: Explicit credential identity replacement
Operators SHALL be able to explicitly consent to replacing the authenticated
Claude identity on an existing account entry. Replacement SHALL preserve settings,
account ID and historical accounting; it SHALL reset current subscription/quota
observations, cooldowns and native resource ownership. Ordinary reconnect SHALL
continue to reject identity mismatches without explicit consent. Replacement SHALL
advance credential generation and the retained identity generation atomically.

#### Scenario: Reauthorize a changed identity
- **WHEN** fresh OAuth or imported credentials authenticate a different identity and replacement consent is supplied
- **THEN** the selected entry receives the credentials while its settings and historical accounting remain intact

#### Scenario: Stale OAuth completion
- **WHEN** the account generation changed after a reconnect flow started
- **THEN** completion cannot replace credentials or clear ownership/state

#### Scenario: Old provider state
- **WHEN** history contains search state issued before identity replacement
- **THEN** completed search history is projected to readable content and active server-bound history is rejected before dispatch

#### Scenario: Late upstream response
- **WHEN** a request from the old identity finishes after replacement
- **THEN** its provenance and quota observations cannot become current for the new identity

#### Scenario: Unchanged identity
- **WHEN** replacement consent is supplied but the authenticated identity is unchanged
- **THEN** reconnect preserves continuation ownership and follows ordinary credential rotation
