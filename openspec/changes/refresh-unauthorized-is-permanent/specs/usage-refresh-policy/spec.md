## ADDED Requirements

### Requirement: Refresh 401 requires re-authentication

A token refresh rejected with HTTP 401 SHALL be a permanent refresh failure whatever its error code, as the Codex
client treats it. When its code is not already a permanent failure code, the failure SHALL carry the code
`refresh_unauthorized` and transition the account to `reauth_required`. A rejection with a permanent failure code
SHALL keep that code and its status.

#### Scenario: 401 with an unknown code
- **WHEN** the refresh endpoint answers 401 with the code `token_revoked`
- **THEN** the refresh error is permanent with code `refresh_unauthorized` and the account becomes `reauth_required`

#### Scenario: 401 with a deactivation code
- **WHEN** the refresh endpoint answers 401 with the code `account_deactivated`
- **THEN** the refresh error keeps that code and the account becomes `deactivated`

#### Scenario: Server error
- **WHEN** the refresh endpoint answers 500 without a permanent failure code
- **THEN** the refresh error is transient
