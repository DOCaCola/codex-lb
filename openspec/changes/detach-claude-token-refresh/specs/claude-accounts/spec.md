## MODIFIED Requirements

### Requirement: Refresh rotation ownership
Refresh MUST use durable cross-worker ownership and generation checks. A dispatched refresh MUST settle independently of the request that started it; requests in the same worker SHALL share it. Explicit invalidation MUST require reauthentication; definitive transient rejections MUST permit a later retry after backoff. Uncertain consumption MUST NOT blindly replay the refresh token, and known expired access tokens MUST NOT be dispatched.

#### Scenario: Ambiguous refresh outcome
- **WHEN** a refresh dispatch times out or the worker dies with a recorded intent
- **THEN** later workers report uncertain credential state instead of rotating the same grant again

#### Scenario: Caller cancelled during refresh
- **WHEN** the client request that started a refresh disconnects before Anthropic answers
- **THEN** the refresh still completes and settles, and the account stays ready with the rotated credentials
