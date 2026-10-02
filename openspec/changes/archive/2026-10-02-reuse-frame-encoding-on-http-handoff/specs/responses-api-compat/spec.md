# responses-api-compat Delta

## ADDED Requirements

### Requirement: The HTTP hand-off reuses the frame's encoding

When an oversized `response.create` frame is sent over upstream HTTP, the proxy MUST parse the frame once and MUST NOT serialize again the top-level members that HTTP shaping leaves structurally identical; those members MUST reuse their encoded text from the frame. A member counts as identical only when every nested value has the same JSON type and value. Members that shaping adds, removes or changes MUST be encoded normally. The body sent upstream MUST be semantically identical to a full re-serialization of the shaped request, and byte-identical when the frame is compact ASCII JSON. The transport MUST measure a frame's UTF-8 size once per send and MUST NOT encode an ASCII frame to measure it.

#### Scenario: Unchanged history is sent from the frame's own encoding

- **GIVEN** an oversized frame whose input history HTTP shaping does not change
- **WHEN** it is sent over upstream HTTP
- **THEN** the input member is taken from the frame text without being encoded again
- **AND** the body equals the body a full re-serialization would produce

#### Scenario: A shaped member is encoded again

- **GIVEN** an oversized frame whose instruction messages are normalized or whose Responses Lite metadata is stripped
- **WHEN** it is sent over upstream HTTP
- **THEN** the changed members are encoded from their shaped values
- **AND** the body equals the body a full re-serialization would produce
