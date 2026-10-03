## ADDED Requirements

### Requirement: Native Claude Message Threads continuity
Native thread continuation SHALL require provenance for the previous message ID
scoped by API key and model and SHALL dispatch only to its originating account.
Thread response message ownership SHALL be persisted before the message ID is
published. The gateway SHALL preserve native history, tool names and cache
markers; it SHALL NOT replay history-less continuations on another account.

#### Scenario: Continuation after soft affinity expiry
- **WHEN** a thread continuation references a retained message and session affinity has expired
- **THEN** the original account serves the request using message provenance

#### Scenario: Missing or foreign thread state
- **WHEN** the previous message has no unexpired provenance in the caller's scope
- **THEN** the gateway returns HTTP 404 with a recognizable thread_not_found marker before upstream dispatch, enabling complete-history replay

#### Scenario: Upstream state expired
- **WHEN** a thread continuation receives an explicit missing-thread upstream 404
- **THEN** the gateway preserves the 404 and publishes the thread_not_found marker without account cooldown or account rotation

#### Scenario: Unrelated not found
- **WHEN** an upstream 404 does not identify missing thread state
- **THEN** it remains an ordinary upstream error
