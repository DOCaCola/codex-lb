# responses-api-compat Delta

## ADDED Requirements

### Requirement: Explicitly refused replayed ciphertext is removed

When upstream explicitly refuses ciphertext a native request replays, the proxy SHALL remember the SHA-256 digests of the ciphertext that request carried and SHALL remove exactly that ciphertext from later native requests. Only the explicit identities of the account-routing payload-rejection rule qualify; a generic `server_error` MUST NOT. Remembered digests SHALL be kept for 24 hours after their last use, at most 20,000 of them, evicting the least recently used. Removal SHALL drop a refused `reasoning` item, replace a refused `compaction` or `compaction_summary` item with a user message stating that the earlier summary is unavailable, and replace a refused `encrypted_content` part of a `function_call_output`, `custom_tool_call_output` or `agent_message` with the text part `[encrypted content omitted]`. Ciphertext with other digests SHALL pass unchanged.

A refused request SHALL be re-sent at most once without the refused ciphertext, on HTTP streaming, compaction, direct WebSocket and the HTTP bridge, when the refusal arrived before any output (on HTTP before any response event; on WebSocket and the bridge before `response.created` or after it without output) and the sent body carried ciphertext not already remembered. A direct WebSocket request anchored with `previous_response_id` SHALL be re-sent as its retained full-history body without the anchor; without such a body the refusal reaches the client. The bridge SHALL apply its generic replay rules for anchored requests. The retry MUST NOT write account health or exclude the account, and the client SHALL observe a single response lifecycle. A refusal of the retry SHALL reach the client.

Checkpoint handoff requests SHALL NOT be remembered, stripped or retried. Upstream readers SHALL take the operation from the request state captured in the request task.

#### Scenario: Refused tool output is replaced on the retry

- **GIVEN** a WebSocket request replaying an encrypted function output
- **WHEN** upstream accepts it and then fails it without output with `invalid_encrypted_content`
- **THEN** the request is re-sent once on the same account with that part replaced by `[encrypted content omitted]`
- **AND** the client observes one response lifecycle ending in `response.completed`

#### Scenario: Refused reasoning is dropped from an anchored follow-up

- **GIVEN** an anchored WebSocket follow-up whose input carries encrypted reasoning
- **WHEN** upstream refuses that reasoning as unverifiable
- **THEN** the retry is the retained full-history body without `previous_response_id` and without the reasoning item

#### Scenario: Later requests are stripped proactively

- **GIVEN** ciphertext upstream refused earlier
- **WHEN** a later native request carries it
- **THEN** it is removed before the request is sent

#### Scenario: A refused retry reaches the client

- **GIVEN** a request already re-sent without refused ciphertext
- **WHEN** upstream refuses the retry
- **THEN** the refusal reaches the client and the request is not sent again

#### Scenario: Checkpoint handoff is untouched

- **GIVEN** a checkpoint handoff request
- **WHEN** upstream refuses its checkpoint
- **THEN** the refusal surfaces unchanged and no digest is remembered
