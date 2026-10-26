## MODIFIED Requirements

### Requirement: Security-work authorization errors can route to authorized accounts

When an upstream Responses request fails because the work requires cybersecurity authorization, codex-lb MUST retry the request on an account marked as security-work-authorized when the request can be safely replayed on a different account. The retry MUST exclude the account that produced the authorization error. codex-lb MUST recognize such a failure by its error code, `cyber_policy` or `security_work_authorization_required`, and MUST NOT infer it from the error message. The failure forwarded to the client and recorded in the request log MUST keep the upstream error code.

#### Scenario: Unpinned stream request retries on an authorized account

- **WHEN** an unpinned streamed Responses request fails with a security-work authorization error on an account that is not security-work-authorized
- **AND** at least one eligible security-work-authorized account is available
- **THEN** codex-lb emits a non-terminal `codex_lb.warning` with `code="security_work_authorization_required"` and `action="retry_security_work_authorized"`
- **AND** codex-lb retries the request with account selection restricted to security-work-authorized accounts

#### Scenario: Refusal recognized by code only

- **WHEN** an upstream error has the code `cyber_policy`
- **THEN** codex-lb treats it as a security-work authorization error
- **AND** an error with another code is not treated as one, whatever its message says

#### Scenario: No authorized account is available

- **WHEN** codex-lb attempts a security-work-authorized retry
- **AND** no security-work-authorized accounts are available
- **THEN** codex-lb emits a non-terminal `codex_lb.warning` with `code="no_security_work_authorized_accounts"` and `action="forward_original_security_work_error"`
- **AND** codex-lb returns the original security-work authorization error with its upstream code
- **AND** codex-lb does not send the request to any other account

#### Scenario: Pinned requests are not moved to another account

- **WHEN** a security-work authorization error occurs for a request pinned by file ownership or previous-response ownership
- **THEN** codex-lb MUST NOT replay the request on a different account
- **AND** the client receives the original security-work authorization failure.

#### Scenario: WebSocket replay releases the response-create gate

- **WHEN** a downstream websocket request is eligible for security-work replay
- **THEN** codex-lb releases the request's response-create gate before scheduling the replay
- **AND** the replay can acquire the gate instead of blocking behind the failed first attempt

## ADDED Requirements

### Requirement: Native requests carry the selected account's cyber access program

codex-lb MUST own the `access_programs` field of native Responses and compaction requests. For the account that serves a request, it MUST send the cyber program a stock Codex client would select from that account's catalog entry for the requested model, treating the account's security-work authorization as the Daybreak setting. The program MUST be derived again whenever the request is sent on a different account, and the field MUST NOT make a request account-bound for failover or replay.

#### Scenario: Authorized account with Daybreak

- **WHEN** the serving account is marked security-work-authorized
- **AND** its catalog lists `daybreak_blue` or `daybreak_red` for the model
- **THEN** the request carries `access_programs: {"cyber": "daybreak_blue"}`, or `daybreak_red` when only that is listed

#### Scenario: Standard program

- **WHEN** the serving account is not security-work-authorized, or its catalog lists no Daybreak program for the model
- **AND** its catalog lists `standard` for the model
- **THEN** the request carries `access_programs: {"cyber": "standard"}`

#### Scenario: No advertised program

- **WHEN** the serving account's catalog lists no cyber program for the model
- **THEN** the request carries no `access_programs` field, whatever the client sent

#### Scenario: Account switch restamps the program

- **WHEN** a request is replayed or failed over to another account
- **THEN** its `access_programs` field is replaced with the program for the new account
