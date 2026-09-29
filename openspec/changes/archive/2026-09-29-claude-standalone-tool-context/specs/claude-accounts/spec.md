## ADDED Requirements

### Requirement: Portable standalone tool-output context
Translated Claude Responses over HTTP and WebSocket SHALL preserve a function/custom-tool output with a nonempty call identifier and no corresponding call anywhere in the expanded input as explicitly labeled user context, including supported text and images. The label SHALL identify the original output kind and call identifier. Projection MUST NOT invent a tool call, tool result or signed reasoning, and MUST NOT mutate retained logical history. Real tool results SHALL remain paired exactly once with preceding pending calls. Malformed identifiers, duplicate paired results, outputs preceding their calls and interrupted or incomplete tool cycles MUST fail before dispatch. Standalone context MUST NOT discharge an active pending call. Rejection diagnostics SHALL include the request identifier, item index, output kind, classification, a bounded call-identifier fingerprint and pending-call count, without content or credentials. Native Messages and authenticated continuation/ownership rules SHALL remain unchanged.

#### Scenario: Delegation context without a call
- **WHEN** a Codex request begins with standalone tool output followed by a user instruction
- **THEN** Claude receives labeled user context containing the output and instruction, not an orphan tool_result

#### Scenario: Valid tool continuation
- **WHEN** a retained previous response contains the call corresponding to the submitted output
- **THEN** continuation expansion restores the pair and Claude receives a real tool_use/tool_result cycle

#### Scenario: Duplicate or out-of-order output
- **WHEN** an output repeats a consumed result or precedes its corresponding call
- **THEN** the request fails before upstream dispatch with content-free classification diagnostics

#### Scenario: Incomplete active cycle
- **WHEN** standalone output arrives while a different call remains pending
- **THEN** the request fails without inventing a result or treating standalone context as completion of that call
