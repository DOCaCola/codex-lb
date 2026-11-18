## ADDED Requirements

### Requirement: Claude refresh responses may omit the refresh token
A Claude token refresh response without a `refresh_token` SHALL keep the current refresh token (RFC 6749 section 6). A response that carries a refresh token SHALL replace it. The authorization-code exchange SHALL require a refresh token.

#### Scenario: Refresh token not rotated
- **WHEN** a Claude refresh response carries an access token but no refresh token
- **THEN** the account stores the new access token with its current refresh token and stays ready

#### Scenario: Sign-in without refresh token
- **WHEN** the authorization-code exchange answers without a refresh token
- **THEN** the sign-in fails
