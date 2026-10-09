## ADDED Requirements

### Requirement: Coherent Claude wire policy
Outbound Claude session headers and structured body session metadata MUST use the
same account/client/conversation-bound identity, stable across token refresh.
Projection MUST NOT mutate logical history or unrelated metadata. Malformed or
unsupported session metadata MUST fail before credential refresh or dispatch.
Native negotiated beta tokens and reviewed helper, agent and compaction hints
SHALL survive forwarding without unsolicited thinking, effort or tool activation.
Native request IDs and retry counts SHALL be preserved independently of gateway
attempt IDs. Native helper/count-token recognition MUST NOT require the main
agent system identity when their supported endpoint/profile signals are present.
Synthesized Messages SHALL advertise a timeout; count_tokens SHALL not synthesize
that field. Transport MUST own compression negotiation.

#### Scenario: Native session metadata
- **WHEN** a native request carries structured session and parent-session metadata
- **THEN** both are scoped consistently with the upstream session header without changing logical history

#### Scenario: Native feature negotiation
- **WHEN** native thinking or output configuration is forwarded
- **THEN** the gateway preserves negotiated betas without inferring extra thinking or tool features

#### Scenario: Helper request
- **WHEN** a recognized native helper lacks the main CLI system identity
- **THEN** its supported body and caller hints are preserved instead of relocated

#### Scenario: Unsupported metadata
- **WHEN** session metadata cannot be safely projected
- **THEN** preparation fails explicitly before token refresh or upstream dispatch
