## ADDED Requirements

### Requirement: Reconnect identity diagnostics
Credential import and OAuth reconnect SHALL distinguish a different authenticated
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
