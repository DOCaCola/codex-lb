## ADDED Requirements

### Requirement: Account-backed stream wrappers close the stream they wrap
Every async-generator wrapper that consumes an account-backed upstream stream on its way to the response body MUST close the stream it wraps when it exits, whether it completes, raises or is closed. A wrapper that raises an error from the middle of the chain MUST therefore release the account stream lease before the error leaves the chain, and closing the outermost stream MUST reach the generator that holds the lease. Release MUST NOT depend on garbage collection of abandoned generators.

#### Scenario: Native transport failure raised by the normalizer
- **GIVEN** a native Codex HTTP Responses stream on an account
- **WHEN** the upstream transport fails and the public normalizer raises `stream_incomplete`
- **THEN** the account's stream lease is released before the error reaches the response layer

#### Scenario: Client closes the stream early
- **GIVEN** an account-backed Responses or chat-completions stream that has delivered its first event
- **WHEN** the outermost stream is closed before the upstream finishes
- **THEN** the account's stream lease is released
