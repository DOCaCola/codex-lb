## MODIFIED Requirements

### Requirement: Interrupted tool calls receive synthetic outputs on anchored follow-ups
The service MUST track tool-call items completed by a streamed response that may still require a tool output — `function_call`, `custom_tool_call`, and `apply_patch_call` — together with each call's item type. When a follow-up `response.create` anchors on that completed response via `previous_response_id` and its input omits an output item for a tracked call id, the service MUST prepend a synthetic interrupted output item whose type matches the originating call type (`function_call` -> `function_call_output`, `custom_tool_call` -> `custom_tool_call_output`, `apply_patch_call` -> `apply_patch_call_output`) before forwarding the request upstream. This applies to the direct WebSocket route and to the HTTP responses bridge session path.

#### Scenario: interrupted custom tool call on the WebSocket route
- **GIVEN** a WebSocket `response.create` turn completes with a `custom_tool_call` item whose output was never sent (the turn was interrupted)
- **WHEN** the next `response.create` on the same session references that response via `previous_response_id` without a `custom_tool_call_output` for the pending call id
- **THEN** the service prepends a synthetic `custom_tool_call_output` item for that call id to the upstream input
- **AND** the follow-up does not fail with an upstream `No tool output found for custom tool call` error

#### Scenario: interrupted custom tool call on the HTTP bridge
- **GIVEN** an HTTP bridge session completes a response containing a `custom_tool_call` item whose output was never sent
- **WHEN** the next bridge request anchors on that response id (client-sent or proxy-injected `previous_response_id`) without an output item for the pending call id
- **THEN** the service prepends a synthetic `custom_tool_call_output` item for that call id to the upstream input

#### Scenario: interrupted function call keeps existing output type
- **WHEN** the pending tool call recorded from the previous response is a `function_call`
- **THEN** the synthetic interrupted output item is a `function_call_output` (existing behavior preserved)

#### Scenario: follow-up that carries the tool output is not modified
- **WHEN** the anchored follow-up input already contains a `function_call_output`, `custom_tool_call_output`, or `apply_patch_call_output` item for a pending call id
- **THEN** the service does not inject a synthetic output for that call id

#### Scenario: injected bridge outputs stay subject to the request size guard
- **GIVEN** an HTTP bridge follow-up whose serialized `response.create` is close to the upstream byte limit
- **WHEN** synthetic interrupted outputs are injected
- **THEN** the service prepares the upstream request from the injected payload so the `response.create` slim/size guard runs against the bytes actually sent upstream
- **AND** an injected frame above the WebSocket limit uses upstream HTTP, subject to the Responses HTTP body budget

#### Scenario: stored input context reflects the injected upstream input
- **WHEN** an HTTP bridge follow-up gains synthetic interrupted outputs
- **THEN** the input item count, input fingerprint, and request usage budget recorded for the request are computed from the injected upstream-shaped input, so later full-resend/anchor comparisons on the same bridge session match what upstream actually stored

#### Scenario: unfingerprinted input turns keep the WebSocket continuity anchor
- **GIVEN** a WebSocket turn whose request input yields no prefix fingerprint (a string input — normalized to a single user message at request validation — or an empty input list)
- **WHEN** the response completes with pending tool-call items
- **THEN** the continuity state still records the completed response id and the pending tool-call metadata for all tracked call types, clearing only the prefix count/fingerprint pair
- **AND** a follow-up that anchors on that response id receives the synthetic interrupted outputs instead of leaking the upstream missing-tool-output 400

#### Scenario: local previous-response recovery retry keeps injected outputs
- **GIVEN** an HTTP bridge submit whose payload gained synthetic interrupted outputs and which fails before yielding with a previous-response continuity error
- **WHEN** the local recovery path re-prepares the anchored retry request
- **THEN** the synthetic interrupted outputs are re-injected from the failed session's pending tool-call state, so the recovered submit does not reintroduce the upstream missing-tool-output failure

#### Scenario: replayed apply_patch prefix is trimmed on anchored bridge follow-ups
- **GIVEN** an HTTP bridge follow-up that anchors via `previous_response_id` on the bridge's latest durable response and replays the `apply_patch_call` that response produced, followed by its `apply_patch_call_output`
- **WHEN** the bridge trims the previous-response prefix already covered by the anchor
- **THEN** `apply_patch_call` and `apply_patch_call_output` items are recognized by the trim exactly like the `function_call` and `custom_tool_call` variants, matching the WebSocket route's replay trim

#### Scenario: owner-forward failover recovery injects from local session state when available
- **GIVEN** a multi-instance bridge where an anchored follow-up is forwarded to the remote owner instance and the relay fails before yielding any bytes
- **WHEN** the local instance recovers by rebinding a local bridge session and resubmitting the anchored request
- **THEN** the service injects synthetic interrupted outputs when the rebound local session still holds the pending tool-call state for the anchored response id (for example after ownership flapped back to this instance)

#### Scenario: owner-forward failover recovery without local pending state is a known bounded gap
- **GIVEN** the same owner-forward failure, where the pending tool-call metadata exists only in the remote owner instance's memory (the durable bridge store does not persist pending call ids)
- **WHEN** the local recovery rebinds a fresh session that has no pending tool-call state
- **THEN** the anchored recovery request is resubmitted unmodified, without fabricated tool outputs (matching pre-injection behavior)
- **AND** if upstream rejects it with a missing-tool-output error, the extended classifier masks it as a retryable continuity failure instead of surfacing the raw upstream 400

## ADDED Requirements

### Requirement: Anchored follow-ups trim only the anchored response's own output
When a `response.create` carries `previous_response_id` and its input starts with an echo of the anchored response's output, the service MAY drop that echo before forwarding, but only through the last tool call (`function_call`, `custom_tool_call` or `apply_patch_call`) that the anchored response itself produced, matched by `call_id` and call type. Reasoning items and assistant messages before that call belong to the echo. The first tool call the anchored response did not produce, or any other item, MUST end the trim, and the service MUST NOT trim when no produced call is found or no tool output follows the cut. The direct WebSocket route MUST trim only when `previous_response_id` is the continuity state's last completed response and MUST use the call types recorded for it. The HTTP bridge MUST trim only when `previous_response_id` is the durable bridge row's latest response and that row holds a verified call manifest. In every other case the input MUST be forwarded unchanged.

#### Scenario: client-authored tool exchange survives an anchored follow-up
- **GIVEN** a WebSocket response completed with tool call `call_repeat`
- **WHEN** the anchored follow-up carries a `function_call` the response did not produce, its output, and the output for `call_repeat`
- **THEN** the upstream input contains the client-authored call, its output and the `call_repeat` output unchanged

#### Scenario: mixed prefix is trimmed through the recorded call only
- **GIVEN** a WebSocket response completed with tool call `call_repeat`
- **WHEN** the anchored follow-up starts with the echoed reasoning and `call_repeat`, followed by a client-authored call and both outputs
- **THEN** the upstream input starts at the client-authored call

#### Scenario: unattributable echo is forwarded whole
- **GIVEN** an anchored follow-up whose `previous_response_id` is not the last completed response known to the route, or an HTTP bridge row without a verified call manifest
- **WHEN** the input starts with call-shaped items and tool outputs
- **THEN** the service forwards the input unchanged
