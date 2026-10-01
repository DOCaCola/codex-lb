## ADDED Requirements

### Requirement: Inter-agent messages are source user messages
Model-source Responses forwarding SHALL send plaintext `agent_message` items as user messages: Codex's agent-message header naming the recipient and sender, followed by the original content. An `agent_message` with an `encrypted_content` part SHALL fail with `nonportable_agent_message`.

#### Scenario: Child reports to a source-served parent
- **WHEN** a request to a model source contains a plaintext `agent_message`
- **THEN** the source receives a user message with the sender header and that text
