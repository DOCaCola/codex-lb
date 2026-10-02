# responses-api-compat Delta

## ADDED Requirements

### Requirement: Proxy-injected anchors are scoped to their upstream connection

The proxy MUST treat a `previous_response_id` that it injects (one the client did not send) as valid only on the upstream connection that completed that response, because upstream keeps `store=false` responses only in that connection's memory. Every upstream WebSocket connection and every HTTP bridge session connection MUST carry an identity, a reconnect MUST assign a new one, and the proxy MUST record the completing connection with each injectable anchor. Account ownership alone MUST NOT make an anchor injectable.

Immediately before a `response.create` is sent, when its injected anchor was completed on a different connection than the one about to send it, the proxy MUST withdraw the anchor and send the request's verified unanchored full replay. When no verified replay exists, the proxy MUST fail the turn locally before anything reaches upstream: WebSocket turns with `previous_response_not_found` (`invalid_request_error`, HTTP 404) and HTTP bridge requests with `bridge_previous_response_not_found` (HTTP 404). This local refusal MUST NOT be replayed over another transport, and MUST NOT be sent without its context.

On HTTP bridge reconnect the proxy MUST clear the session's completed-response anchor and pending tool calls and unregister their previous-response aliases. A new HTTP bridge session MUST NOT be seeded with a durable response ID as its anchor. Owner-forward recovery MUST inject an anchor only when the local session completed that response.

Client-supplied `previous_response_id` values MUST NOT be withdrawn or rewritten by this rule. Same-connection anchoring and prefix trimming MUST remain unchanged.

#### Scenario: Same-connection follow-up keeps the injected anchor

- **GIVEN** a WebSocket or HTTP bridge turn completed on upstream connection C
- **WHEN** the next turn is sent on C
- **THEN** the proxy may inject the completed response ID and trim the stored prefix

#### Scenario: Replacement connection sends the full replay

- **GIVEN** a turn completed on connection C and the proxy prepared an injected anchor for the follow-up
- **AND** the follow-up has a verified unanchored full replay
- **WHEN** it is sent on replacement connection D
- **THEN** its `response.create` omits `previous_response_id`
- **AND** its input is the full replay

#### Scenario: Delta without a replay fails closed locally

- **GIVEN** a follow-up relies on an injected anchor from closed connection C for its context
- **AND** it has no verified unanchored replay
- **WHEN** it would be sent on a different connection
- **THEN** nothing is sent upstream
- **AND** the client receives a 404 previous-response-not-found error

#### Scenario: HTTP bridge reconnect forgets the old anchor

- **GIVEN** an HTTP bridge session completed a response on its connection
- **WHEN** the session reconnects upstream, on the same account or another
- **THEN** its completed-response anchor and pending tool calls are cleared
- **AND** no later request on the session injects that response ID

## MODIFIED Requirements

### Requirement: Fresh durable HTTP bridge preserves client-unanchored full resends

The service MUST preserve a client-unanchored full resend as the first request
on a fresh durable HTTP bridge. This applies when the request resolves a hard
durable conversation, has no client-supplied `previous_response_id`, has a
stored prefix matching that durable conversation, and has neither a reusable
local bridge nor a forwardable remote owner. The input projected through the
existing fresh-replay bookkeeping filter MUST also either retain completed
assistant output before fresh user input or have a suffix consisting only of
complete, self-contained direct tool call/output pairs that exactly match a
durable manifest of every call ID and call type emitted by the prior response.
The manifest MUST include every observed tool-call `output_item.added` event,
MUST require a matching `output_item.done` event with the same call ID and type,
MUST reconcile any tool calls present in terminal response output, and MUST be
persisted atomically with that response's durable alias. An incomplete,
conflicting, or malformed lifecycle MUST persist an unknown manifest rather
than a partial one. Duplicate call IDs in added, done, or terminal output MUST
invalidate the manifest even when their call types match. The serialized
manifest MUST bind its call map to the exact durable response ID, and a response
ID mismatch MUST be treated as an unknown manifest so rolling-upgrade writers
that do not know the manifest column cannot leave stale calls on a newer
response.
If a response contains a client-settled call type that the direct tool-loop
proof cannot represent, including `computer_call` or `mcp_approval_request`,
the service MUST treat the entire manifest as unknown rather than persist a
partial manifest for any parallel supported calls.
The service MUST submit that safe original full resend without adding
`previous_response_id`, MUST retain the durable preferred owner and hard
affinity, MUST NOT move the request through account-neutral replay, and MUST NOT
trim the stored prefix before that first send.

If the matching cumulative input omits prior output, contains an incomplete or
orphaned tool call/output sequence, omits any call in the durable manifest,
reuses a stored-prefix call ID, has no known durable manifest, or otherwise
lacks either safe context shape, no full-resend proof is created. Because the
fresh connection cannot resolve the durable anchor, the service MUST still
submit the client's cumulative input without adding `previous_response_id` and
without trimming it, under the existing owner and fail-closed routing for
requests without that proof. A delta-only request on a fresh connection after a
durable anchor MUST fail closed locally as defined by the connection-scoped
anchor requirement.

The service MUST NOT seed the newly created local session with the old durable
response. Once the fresh request completes, ordinary live-session continuity
and trimming MAY resume from the newly completed response. Client-supplied
anchors, owner-unavailable handling, and existing account-neutral replay
eligibility remain unchanged.

Complete full-resend eligibility MUST be represented by an immutable request-local proof that binds the current payload fingerprint to the durable session ID, owner account, latest response ID, stored count, stored fingerprint, and pending-tool-call manifest identity. The proof MUST be created only by the count, fingerprint, and retained-output or response-bound pending-tool-call verifier; it MUST NOT be accepted from a caller, persisted, deserialized, or ordinarily constructed, and mutation or durable-state substitution MUST invalidate it.

When that proof authorizes a fresh owner-bound bridge and the incoming affinity comes from a broad session header, the service MUST omit the downstream session/turn aliases from the fresh upstream connection and MUST NOT consult the broad legacy sticky row during account selection. It MUST retain the durable canonical bridge key, require the durable owner account, preserve Codex session behavior for subsequent turns, and leave the broad sticky row unchanged. Conflicting specific turn-state, previous-response, bridge, or file owners MUST still fail closed. This broad-alias reconciliation MUST NOT itself rebind the request to another account; existing account-neutral full-resend recovery after a genuine owner-unavailable result remains governed by its separate replay-safety requirements.

#### Scenario: Full resend opens a fresh bridge without a durable anchor
- **GIVEN** a client-unanchored full resend has a verified stored prefix and retained completed assistant output for a hard durable conversation
- **AND** no reusable local bridge or forwardable remote owner exists
- **WHEN** the service creates a fresh upstream WebSocket on the durable owner
- **THEN** its first `response.create` omits `previous_response_id`
- **AND** its input contains the original full resend
- **AND** its hard session affinity is retained

#### Scenario: Tool-loop resend does not require an assistant-message replay boundary
- **GIVEN** a verified client-unanchored full resend continues a tool loop with complete self-contained direct call/output pairs but no completed assistant-message boundary
- **AND** those calls and outputs exactly settle the durable prior-response call manifest
- **WHEN** it starts on a fresh durable bridge
- **THEN** the service submits the original request once on the durable owner
- **AND** retained-output checks used for cross-account replay do not block or rewrite that first send

#### Scenario: Omitted parallel tool call remains anchored
- **GIVEN** the durable prior-response manifest contains two parallel call IDs
- **WHEN** a matching cumulative input carries a complete call/output pair for only one ID
- **THEN** the service does not classify the suffix as a complete tool-loop resend
- **AND** it submits the cumulative input without `previous_response_id`

#### Scenario: Incomplete tool-call lifecycle keeps manifest unknown
- **GIVEN** a response emits added events for two parallel tool calls
- **AND** only one call reaches a matching done event before `response.completed`
- **WHEN** the durable response alias is persisted
- **THEN** its tool-call manifest is unknown rather than a one-call partial manifest
- **AND** a later direct tool-loop full resend creates no full-resend proof

#### Scenario: Unsupported parallel client-settled call keeps manifest unknown
- **GIVEN** a response emits a supported direct call and a parallel client-settled call that the replay proof cannot represent
- **WHEN** the durable response alias is persisted
- **THEN** its tool-call manifest is unknown rather than a partial supported-call manifest
- **AND** a later resend that settles only the supported call creates no full-resend proof

#### Scenario: Legacy durable row remains anchored
- **GIVEN** a durable response row predates the call-manifest migration or otherwise has an unknown manifest
- **WHEN** a matching cumulative input contains direct tool call/output items without a completed assistant-message boundary
- **THEN** no full-resend proof is created
- **AND** the input is submitted without `previous_response_id`

#### Scenario: Older writer advances response without manifest
- **GIVEN** a durable row has a response-bound tool-call manifest
- **WHEN** an older rolling-upgrade writer advances `latest_response_id` without updating the manifest column
- **THEN** readers treat the mismatched manifest as unknown
- **AND** a later direct tool-loop full resend creates no full-resend proof

#### Scenario: Cumulative prompt without prior output remains anchored
- **GIVEN** a matching cumulative input contains fresh user input but omits the prior assistant output
- **WHEN** no reusable bridge exists for its hard durable conversation
- **THEN** no full-resend proof is created
- **AND** the service submits the cumulative input without `previous_response_id` and without trimming

#### Scenario: Failed owner forwarding preserves omitted response context
- **GIVEN** a matching cumulative input omits prior assistant output and initially resolves to a forwardable durable owner
- **WHEN** owner forwarding fails before any downstream output and the service performs local takeover
- **THEN** the local recovery request does not inject the durable `previous_response_id`, which the new local connection did not complete
- **AND** it submits the cumulative input without trimming

#### Scenario: Refreshed takeover context no longer matches the resend
- **GIVEN** owner forwarding fails and the refreshed durable takeover row has different stored-input metadata
- **WHEN** the cumulative input cannot prefix-match that refreshed row
- **THEN** the service fails closed instead of pairing the refreshed response ID with stale prefix metadata

#### Scenario: Refreshed takeover account replaces stale routing
- **GIVEN** owner forwarding fails and the refreshed durable takeover row names a different account
- **WHEN** the service performs local takeover
- **THEN** the recovery session requires the refreshed account rather than the initial stale account
- **AND** a refreshed account that conflicts with another required owner fails closed

#### Scenario: Live bridge trimming remains unchanged
- **GIVEN** the durable conversation still has a reusable live bridge
- **WHEN** a trimmable full resend continues that live session
- **THEN** the existing session-level anchor and prefix-trimming behavior remains available

#### Scenario: stale broad session owner does not loop a verified full resend
- **GIVEN** a hard durable session is owned by account B and records a latest
  response ID, positive input count, and full fingerprint
- **AND** no live local bridge or active remote owner remains
- **AND** a broad legacy session-header sticky row points at account A
- **WHEN** the client sends a full resend whose stored prefix matches both
  durable values and whose suffix retains completed prior output before fresh
  input or exactly settles the response-bound pending-tool-call manifest
- **THEN** the service opens the fresh bridge on account B
- **AND** it submits the complete payload without `previous_response_id`
- **AND** it does not consult or rewrite the broad legacy row
- **AND** it omits downstream session and turn aliases from the fresh upstream
  connection

#### Scenario: recovered bridge keeps incremental continuity
- **GIVEN** a verified full resend established a fresh owner-bound bridge
- **WHEN** that bridge completes and a later incremental turn arrives
- **THEN** the later turn remains on the same account
- **AND** the bridge may use the newly established response anchor

#### Scenario: incomplete resend cannot bypass a broad owner conflict
- **GIVEN** a durable owner conflicts with a broad legacy session owner
- **WHEN** the input prefix does not match, retained prior output is absent, the
  payload or durable identity changes after verification, or the request is
  incremental
- **THEN** no full-resend proof authorizes reconciliation
- **AND** the request retains existing fail-closed owner behavior

#### Scenario: specific owner conflict remains fail-closed
- **GIVEN** a verified full resend also contains a turn-state,
  previous-response, bridge, or file owner that conflicts with the durable
  owner
- **WHEN** continuity is resolved
- **THEN** the request fails with `continuity_owner_conflict`
- **AND** the broad-session reconciliation does not choose either account
