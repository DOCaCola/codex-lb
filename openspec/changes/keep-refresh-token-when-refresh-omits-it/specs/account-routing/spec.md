## ADDED Requirements

### Requirement: Refresh responses may omit the refresh token
An OpenAI token refresh response without a `refresh_token` SHALL keep the refresh token that was sent, as RFC 6749 section 6 and the Codex client specify. A response that carries a refresh token SHALL replace the stored one. The access token and ID token SHALL remain required.

#### Scenario: Refresh token not rotated
- **WHEN** a refresh response carries an access token and ID token but no refresh token
- **THEN** the account stores the new access and ID tokens and keeps its current refresh token

#### Scenario: Refresh token rotated
- **WHEN** a refresh response carries a new refresh token
- **THEN** the account stores the new refresh token
