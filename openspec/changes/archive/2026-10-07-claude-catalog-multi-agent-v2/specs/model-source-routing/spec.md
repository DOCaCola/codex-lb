## MODIFIED Requirements

### Requirement: Inter-agent messages are source user messages
Model-source Responses forwarding SHALL send plaintext `agent_message` items as user messages carrying the item's content unchanged. Codex's agent-message header naming the recipient and sender is part of that content; the proxy MUST NOT add another. An `agent_message` with an `encrypted_content` part SHALL fail with `nonportable_agent_message`.

#### Scenario: Child reports to a source-served parent
- **WHEN** a request to a model source contains a plaintext `agent_message`
- **THEN** the source receives a user message with that content, including Codex's header, exactly once
