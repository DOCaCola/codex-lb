## ADDED Requirements

### Requirement: Source Responses WebSocket transport
Responses clients SHALL use the same source models over HTTP and WebSocket. The proxy MUST bridge source SSE events into Responses WebSocket messages without requiring a client HTTP downgrade. Both transports MUST enforce the same model/source access and usage settlement. Disconnects MUST cancel and close owned upstream work. Switching to a subscription model MUST retain subscription routing.

#### Scenario: Source turn over WebSocket
- **WHEN** a client sends response.create for a source model
- **THEN** it receives Responses events on the same socket while upstream uses HTTP

#### Scenario: Source then subscription model
- **WHEN** an idle client socket switches from an OpenRouter model to a subscription model
- **THEN** the subscription model uses its normal account and transport selection

### Requirement: Stateless source continuation
For stateless sources the system SHALL reconstruct scoped previous-response history before dispatch and retain complete input and output under bounded private retention. It MUST preserve tool identities and MUST return an actionable previous_response_not_found error if required state is missing. Upstream MUST receive complete history without a previous_response_id or store:true.

#### Scenario: Tool continuation
- **WHEN** a client sends a previous response id with a tool output
- **THEN** the provider receives the preceding conversation and matching tool call exactly once

#### Scenario: Expired continuation
- **WHEN** required retained history has expired
- **THEN** the client receives previous_response_not_found requesting full history and no incomplete request is sent upstream

## MODIFIED Requirements

### Requirement: Source compaction history safety
Source compaction MUST reject unresolved previous-response or conversation handles with an actionable client error requesting materialized history. Source requests MUST reject unreadable native compaction checkpoints rather than replace history with a placeholder. Valid proxy-owned summaries MUST remain portable. Both the dedicated compact endpoint and terminal compaction triggers SHALL use the selected source for summarization.

#### Scenario: Unresolved compact continuation
- **WHEN** source compaction includes a previous-response handle whose history cannot be resolved
- **THEN** the proxy returns a client error without dispatching a summary request

#### Scenario: Retained compact continuation
- **WHEN** source compaction includes a resolvable previous-response handle
- **THEN** the proxy materializes the history before dispatching a stateless summarization request
