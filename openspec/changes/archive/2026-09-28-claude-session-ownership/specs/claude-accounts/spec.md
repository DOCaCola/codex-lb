## ADDED Requirements
### Requirement: Native Claude affinity and signature recovery
Native first-party thinking history SHALL remain unchanged in ordinary requests.
Thinking alone MUST NOT require an unexpired account-owner record. Account
preference SHALL be subordinate to authorization and eligibility. Native server
resource state SHALL retain existing ownership restrictions.
After account rebinding, native server-resource history MUST be rejected while
the session's issuing account is ambiguous, rather than assigned to the new owner.

#### Scenario: Idle thinking conversation
- **WHEN** a native conversation resumes with thinking after affinity expires
- **THEN** it may select an eligible account without altering its thinking

### Requirement: Bounded historical signature recovery
Messages forwarding SHALL retry at most once on an upstream HTTP 400 explicitly
rejecting a thinking-block signature, before output delivery. Recovery SHALL
remove only completed historical thinking, preserve active ordinary and server
tool cycles, and leave all visible content and tool pairs unchanged. If removal
would leave an empty message or no safe change exists, it SHALL return the error.
Generic errors, 429s and latest-assistant-modification errors MUST NOT trigger it.

#### Scenario: Historical rejection
- **WHEN** an upstream rejects an eligible historical thinking signature
- **THEN** one same-target recovery attempt is allowed, without changing accounts

### Requirement: Scoped parent affinity
Native sessions SHALL use explicit session headers or structured session metadata,
reject conflicting identities, and allow an eligible parent's account preference
only within the same authenticated client and model scope.

#### Scenario: Child session
- **WHEN** a child starts without its own affinity and its parent has an eligible account
- **THEN** it prefers the parent's account without overriding hard resource ownership
