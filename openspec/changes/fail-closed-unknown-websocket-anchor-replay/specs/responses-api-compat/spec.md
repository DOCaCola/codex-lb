## MODIFIED Requirements

### Requirement: WebSocket full-resend previous-response misses retry without stale anchor
When a direct WebSocket `response.create` request includes both `previous_response_id` and a self-contained full resend payload, the service MUST retain a safe replay body without `previous_response_id`. If upstream rejects the anchor with `previous_response_not_found` before `response.created`, the service MUST reconnect and replay the retained full payload as a fresh turn instead of forwarding the raw upstream invalid-request error. A payload that only carries incremental tool outputs for tool calls that are not also present in the same request is not self-contained and MUST NOT be replayed as a fresh turn without `previous_response_id`.

A client-anchored payload is a full resend only when its anchor is the connection's last completed response or empty prewarm, that request's input covered its whole context (no anchor, a proxy-injected anchor, or a proven full resend), and the payload restates its stored input prefix. Any other client-anchored payload MUST NOT be replayed as its own input without `previous_response_id`; recorded history MAY complete it.

#### Scenario: full-resend WebSocket follow-up loses just-completed anchor
- **WHEN** a WebSocket `/v1/responses` or `/backend-api/codex/responses` follow-up has `previous_response_id`
- **AND** that anchor is the response this connection last completed, from a request whose input covered its whole context
- **AND** the request payload restates that request's stored input prefix, so it is treated as a full resend
- **AND** upstream emits `previous_response_not_found` before assigning a response id
- **THEN** the service reconnects the upstream WebSocket
- **AND** it replays the same request without `previous_response_id`
- **AND** the downstream client receives the recovered response events, not the raw `previous_response_not_found` error

#### Scenario: output-only WebSocket tool delta is not replayed as a fresh turn
- **WHEN** a WebSocket `/v1/responses` or `/backend-api/codex/responses` follow-up has `previous_response_id`
- **AND** the request payload carries `function_call_output`, `custom_tool_call_output`, or `apply_patch_call_output` items without their matching tool-call items in the same payload
- **AND** upstream emits `previous_response_not_found` before assigning a response id
- **THEN** the service MUST NOT replay that payload as a fresh turn without `previous_response_id`
- **AND** the downstream client receives a retryable continuity failure rather than a fabricated fresh turn

#### Scenario: delta chained to an empty prewarm is not replayed as a fresh turn
- **GIVEN** a direct WebSocket handshake carries `x-codex-turn-metadata` with `request_kind: "prewarm"`
- **AND** a `generate: false` request on that connection completed with zero output tokens
- **WHEN** the next request sets `previous_response_id` to that prewarm and its input does not begin with the prewarm's input
- **AND** the upstream closes or rejects the anchor before `response.created`
- **THEN** the service MUST NOT replay that payload without `previous_response_id`
- **AND** the downstream client receives a retryable failure rather than a turn answered without the prewarm's context

#### Scenario: full resend chained to an empty prewarm stays replayable
- **GIVEN** an empty-output prewarm completed on the connection
- **WHEN** the next request sets `previous_response_id` to that prewarm and its input begins with the prewarm's input
- **THEN** the service MAY replay that payload without `previous_response_id` after an upstream close or anchor rejection

#### Scenario: delta on an anchor from another connection is not replayed as a fresh turn
- **WHEN** a WebSocket `/v1/responses` or `/backend-api/codex/responses` follow-up has `previous_response_id` that this connection never completed
- **AND** the request payload is self-contained but carries only the turn's new items, such as a user message
- **THEN** the service MUST NOT retain an anchorless replay body for that request
- **AND** if upstream emits `previous_response_not_found` before assigning a response id, the downstream client receives `previous_response_not_found` rather than a fresh turn built from the new items alone

#### Scenario: restated delta of a client-anchored completion is completed from recorded history
- **GIVEN** the connection's last completed response came from a request that the client anchored and that carried only a delta
- **WHEN** the follow-up anchors that response and its input restates that delta and adds new items
- **THEN** the service MUST NOT treat the follow-up's input alone as a full resend
- **AND** a replay after `previous_response_not_found` re-sends the recorded history followed by the follow-up's input, without `previous_response_id`

### Requirement: Direct WebSocket records conversation history to make client-anchored deltas re-sendable

On a direct Responses WebSocket connection the proxy MUST record, per connection, the logical history of the last completed response -- the request's materialized input followed by the output items of the completed or interrupted response -- and of the last empty `generate: false` prewarm (its input). A request's materialized input is its own input when it is unanchored, the retained full resend when the proxy injected the anchor or the client sent a proof-gated full resend, and the recorded history followed by the request's input when the client anchors a delta to the recorded response. The history MUST be cleared with the completion anchor it belongs to and MUST NOT be recorded when either the input or the output is unknown.

When the client anchors a delta to a response whose history is recorded, the proxy MUST forward the anchored request unchanged and MUST retain the history followed by the delta, without `previous_response_id`, as the request's retry-safe fresh payload. Upstream resolves a `store=false` anchor only on the connection that produced it, so every replay -- pre-created or accepted, after a capacity terminal or a transport close -- MUST re-send that fresh payload, never the anchored body. When the client later anchors a request to the id it read for a replayed response, which upstream never issued on the current connection, the proxy MUST send that request as the recorded history followed by its delta, without `previous_response_id`.

The fresh payload MUST be serialized like a client body with the same input: when the recorded history carries the first turn's `additional_tools` item it is a Responses Lite body, sent with the Lite marker and reasoning context, and an accepted replay keeps the connection's Lite continuity.

When a replayable output-free terminal is forwarded unchanged because the request's state refuses the replay, the proxy MUST log the refusal reason (other pending requests, a sent sequenced frame, started output, not sent, replay consumed, an anchor without fresh payload, no request body, a foreign response id, or reported output) with the request id and code, and without request or response content.

#### Scenario: A Codex delta follow-up overloaded after acceptance is replayed with its history
- **GIVEN** a direct WebSocket connection whose previous turn completed with recorded input and output
- **AND** the client sends the next turn as `previous_response_id` of that turn plus only its new items
- **WHEN** upstream accepts the turn and then emits an output-free `server_is_overloaded` `error`
- **THEN** the proxy re-sends the recorded history followed by the new items, without `previous_response_id`, once
- **AND** the client observes exactly one `response.created` and a `response.completed` carrying that id

#### Scenario: The turn after a replay is anchored to the visible id
- **GIVEN** a turn whose single-lifecycle replay completed under the id the client read from the first attempt
- **WHEN** the client anchors its next delta to that visible id
- **THEN** the proxy sends the recorded conversation followed by the delta without `previous_response_id`

#### Scenario: A lost anchor of a recorded delta is recovered with the history
- **GIVEN** the client anchors a delta to a turn completed on the connection whose history the proxy recorded
- **WHEN** upstream rejects the anchor with `previous_response_not_found` (or its parameterless `Invalid previous_response_id` form) before `response.created`
- **THEN** the proxy re-sends the recorded history followed by the delta without `previous_response_id` on a fresh upstream connection
- **AND** the client receives the recovered response events, never the continuity error

#### Scenario: A turn chained to an empty prewarm is replayed with the prewarm context
- **GIVEN** an empty `generate: false` prewarm completed on the connection and the client anchors its first turn to it with only the new items
- **WHEN** upstream closes the transport before the turn is accepted
- **THEN** the proxy re-sends the prewarm input followed by the new items without `previous_response_id`

#### Scenario: Unknown history keeps the anchored request non-replayable
- **WHEN** the client anchors a delta to a response whose history the proxy did not record
- **THEN** the request has no fresh payload, the pre-output hold does not apply, and an accepted output-free terminal is forwarded unchanged and logged with the refusal reason `anchored_without_fresh_body`

#### Scenario: History beginning with a Lite tool bundle is replayed as a Lite body
- **GIVEN** the conversation's first turn carried an `additional_tools` item and later turns are marker-only Lite deltas
- **WHEN** a delta is replayed from the recorded history after `previous_response_not_found`
- **THEN** the replay carries the Lite marker and `reasoning.context = "all_turns"`
- **AND** a later marker-only delta anchored to the replay's response id is trusted as Lite

