## ADDED Requirements

### Requirement: Claude Chat routing without upstream Chat capability

An enrolled Claude OAuth source SHALL serve authorized `/v1/chat/completions` requests through its Responses capability without being marked as an upstream Chat Completions source. Existing enabled accounts SHALL be eligible without re-enrollment. Disabled, unauthorized and exhausted Claude pools MUST NOT fall back to OpenAI subscription accounts.

#### Scenario: Existing enrolled account
- **WHEN** an enabled Claude model is requested on the Chat endpoint
- **THEN** the existing Claude account pool handles the request through its normal owner and transport

#### Scenario: Signed Chat tool replay
- **WHEN** a keyed client resends complete Chat tool history matching one live record
- **THEN** Claude receives the original authenticated signed thinking on its original account and model
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures
