## ADDED Requirements

### Requirement: Routed requests name the destination model in the Codex identity
Before dispatching a Responses request to a model source, the proxy SHALL rewrite a Codex identity sentence in `instructions` to name the destination source model's display name. This SHALL apply to the neutral catalog prompt and to a native GPT prompt replayed into a routed subagent. Instructions without a Codex identity sentence MUST be forwarded unchanged, and operator request overrides keep precedence.

#### Scenario: Replayed native prompt
- **GIVEN** a routed request whose instructions begin "You are Codex, an agent based on GPT-6."
- **WHEN** the request is dispatched to source model "Claude Opus 5.5"
- **THEN** the source receives "You are Codex, an agent running on Claude Opus 5.5." in place of that sentence

#### Scenario: Unrelated instructions
- **WHEN** a routed request carries instructions without a Codex identity sentence
- **THEN** the source receives them unchanged
