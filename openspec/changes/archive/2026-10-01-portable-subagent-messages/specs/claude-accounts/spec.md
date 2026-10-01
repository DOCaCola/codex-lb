## ADDED Requirements

### Requirement: Inter-agent messages are Claude user turns
Translated Claude Responses requests SHALL accept `agent_message` items whose content is plaintext and project them as user turns, under the same tool-cycle rules as user messages. The turn SHALL begin with Codex's agent-message header naming the recipient and sender. An `agent_message` with an `encrypted_content` part SHALL fail with `nonportable_agent_message` and SHALL NOT be dropped or forwarded as text.

#### Scenario: Child progress wakes a Claude parent
- **WHEN** a Claude parent's history contains a plaintext `agent_message` from its child after a completed tool cycle
- **THEN** Claude receives the sender header and the message text as a user turn

#### Scenario: Pre-deployment encrypted message
- **WHEN** the history contains an `agent_message` with OpenAI ciphertext
- **THEN** the request fails with `nonportable_agent_message`
