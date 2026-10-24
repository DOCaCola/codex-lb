## MODIFIED Requirements

### Requirement: Native Messages fidelity
Authenticated `/v1/messages` and `/v1/messages/count_tokens` requests for Claude models SHALL preserve supported recognized native body fields, system block order, cache markers, tool identifiers, beta/version metadata, SSE pings, upstream error status and rate-limit information. Caller credentials and hop-by-hop headers MUST NOT reach upstream. Native recognition MUST NOT grant authentication or change global version state. Third-party Messages SHALL use the same explicit OAuth compatibility policy as translated Responses. Unsupported billing semantics MUST fail explicitly rather than silently change spending policy. Thinking blocks signed with a proxy reasoning envelope SHALL be removed before dispatch, and an assistant message left empty SHALL be removed.

#### Scenario: Native extension fields
- **WHEN** a client sends safeguards and corresponding beta metadata
- **THEN** these reach the trusted Anthropic destination without flattening its system array

#### Scenario: Native stream transport failure
- **WHEN** the upstream Messages stream fails after downstream headers were sent
- **THEN** the gateway settles the failed attempt and returns a native SSE error event, not a Responses envelope or successful message_stop

#### Scenario: Switch from a GPT model to Claude
- **WHEN** a Claude Code session switches from a translated GPT model to a Claude model
- **THEN** the native request omits thinking blocks carrying proxy envelopes and keeps all other content unchanged
