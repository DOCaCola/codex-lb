## MODIFIED Requirements

### Requirement: Standalone Codex web search is forwarded faithfully

The proxy SHALL expose `POST /backend-api/codex/alpha/search` through the same
proxy-authenticated Codex control-request path used by other unary Codex control
endpoints. The proxy MUST preserve the inbound request body and query parameters,
MUST apply the existing API-key scope, account selection, token refresh, session
affinity, failover, and upstream-route policies, and MUST forward the request to
the upstream `POST /codex/alpha/search` path. Successful downstream responses
MUST preserve the upstream status and body and MUST include only response
headers allowed by the existing Codex control-response policy. Final non-2xx
responses MUST preserve their status while using the existing Codex control
OpenAI error-envelope normalization. The proxy MUST NOT normalize, rewrite, or
invent a local schema for search requests or responses.

The proxy SHALL derive search identity from the `x-codex-turn-metadata` JSON
header: its `session_id` is the process session and its `thread_id` the logical
thread. When metadata carries no session, the body `id` SHALL be the process
session. With session affinity enabled, a search carrying a thread MUST use the
same thread-locality key, kind and lifetime as the conversation's Responses
turns sent with the equivalent `session-id` and `thread-id` headers; a search
with only a process session MUST use process-session affinity. The request log
MUST record the metadata `thread_id` as conversation, the body `model` as model
when present, and the client IP. Reading these fields MUST NOT alter the
forwarded body.

#### Scenario: authenticated standalone search reaches the upstream Codex path

- **GIVEN** a valid proxy API key and at least one eligible ChatGPT account
- **WHEN** Codex sends `POST /backend-api/codex/alpha/search` with a JSON body and
  query parameters
- **THEN** the proxy forwards the unchanged body and query parameters to
  `POST /codex/alpha/search` using the selected account credentials
- **AND** the downstream client receives the upstream status and body

#### Scenario: unsafe upstream response headers are not exposed

- **WHEN** the upstream search response includes both allowlisted metadata and
  a response header outside the Codex control-response allowlist
- **THEN** the proxy returns the allowlisted metadata
- **AND** it omits the non-allowlisted response header

#### Scenario: final upstream search failures use the control error contract

- **WHEN** upstream search failure handling finishes with a non-2xx response
- **THEN** the proxy preserves the final HTTP status
- **AND** it returns the failure through the existing OpenAI error envelope
- **AND** existing account refresh, health, and failover handling remains active

#### Scenario: unsupported methods do not enter search forwarding

- **WHEN** a client sends a non-POST request to
  `/backend-api/codex/alpha/search`
- **THEN** the request does not enter the upstream search forwarding path

#### Scenario: search follows its conversation's thread account

- **GIVEN** two threads of one Codex process session hold thread locality on
  different accounts
- **WHEN** each thread issues a standalone search whose turn metadata names it
- **THEN** each search is sent with its own thread's account
- **AND** its request log records the thread as conversation, the body model and
  the client IP

#### Scenario: search without turn metadata follows its process session

- **GIVEN** a process session holds session affinity on an account
- **WHEN** a standalone search carries no turn metadata and that session as body `id`
- **THEN** the search is sent with that account
