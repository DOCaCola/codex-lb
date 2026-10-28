## ADDED Requirements

### Requirement: OpenAI output replay stays with OpenAI
OpenRouter Responses projection SHALL remove the `output.encrypted_content` include
value and `encrypted_content` from non-reasoning input items before strict
parameter routing. Other include values, reasoning items and visible history SHALL
be forwarded unchanged. The caller's payload SHALL NOT be mutated.

#### Scenario: Codex switches to an OpenRouter model
- **WHEN** a Codex request for an OpenRouter model includes output.encrypted_content and history with OpenAI message and tool-call ciphertext
- **THEN** OpenRouter receives the visible history and reasoning include without the OpenAI output ciphertext or its include value

