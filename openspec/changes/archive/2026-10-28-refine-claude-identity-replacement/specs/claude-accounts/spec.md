## MODIFIED Requirements

### Requirement: Explicit credential identity replacement
Operators SHALL be able to explicitly consent to replacing the authenticated
Claude identity on an existing account entry. Replacement SHALL preserve settings,
account ID, historical accounting and the discovered model catalog; it SHALL reset
current subscription/quota observations, cooldowns and native resource ownership,
and SHALL mark the catalog due for rediscovery. Ordinary reconnect SHALL continue to
reject identity mismatches without explicit consent, and mismatch errors SHALL name
the replacement option. Replacement SHALL advance credential generation and the
retained identity generation atomically. A request whose account identity is
replaced during preparation or before sending SHALL NOT dispatch: resource-bound
continuations SHALL return their resource error, including replayable
`thread_not_found` for native threads, and other requests SHALL return retryable
503 `claude_identity_changed` with `Retry-After: 1`.

#### Scenario: Reauthorize a changed identity
- **WHEN** fresh OAuth or imported credentials authenticate a different identity and replacement consent is supplied
- **THEN** the selected entry receives the credentials while its settings and historical accounting remain intact

#### Scenario: Routable during rediscovery
- **WHEN** an identity is replaced before the next catalog refresh
- **THEN** selected models remain routable for the new identity and the scheduler rediscovers the catalog

#### Scenario: Stale OAuth completion
- **WHEN** the account generation changed after a reconnect flow started
- **THEN** completion cannot replace credentials or clear ownership/state

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
- **WHEN** replacement consent is supplied but the authenticated identity is unchanged
- **THEN** reconnect preserves continuation ownership and follows ordinary credential rotation

