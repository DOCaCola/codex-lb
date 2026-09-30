## ADDED Requirements

### Requirement: Foreign reasoning at Claude dispatch

Translated Claude Responses SHALL classify provider-specific reasoning before signed-history authentication and account selection. Completed foreign reasoning with readable summary or reasoning_text content SHALL become ordinary historical assistant text, preserving distinct text and ordering without ciphertext, lookup IDs or fabricated thinking signatures. Plaintext-only reasoning SHALL follow the same portable projection. Logical retained history, user/assistant messages and tool pairing MUST remain unchanged. The policy SHALL apply after expansion to HTTP and WebSocket, including replayed continuation.

Foreign encrypted reasoning without readable text, foreign encrypted active reasoning and foreign ciphertext in complete-history compaction MUST fail before dispatch with nonportable_provider_history and the affected input index. A paired tool output MUST NOT count as a new user turn. Purely plaintext compaction SHALL preserve all readable reasoning. Genuine Claude envelopes, including empty-display signed blocks, MUST retain existing client/conversation authentication and account/model ownership. Authentication failures SHALL expose invalid_provider_history with an input index rather than a generic payload message. Conversion diagnostics MUST contain counts only, never reasoning or opaque contents.

#### Scenario: Sol-to-Opus historical switch
- **WHEN** completed OpenAI reasoning has a readable summary and encrypted_content before a new user message
- **THEN** Claude receives the summary as historical assistant text, no foreign ciphertext or synthetic thinking, and retained history remains unchanged

#### Scenario: Opaque-only history
- **WHEN** foreign encrypted reasoning has no readable summary or content
- **THEN** preparation returns nonportable_provider_history at its input index without dispatch or data deletion

#### Scenario: Active foreign tool continuation
- **WHEN** foreign encrypted reasoning belongs to the active assistant turn and is followed only by paired tool output
- **THEN** preparation fails explicitly instead of fabricating a signed continuation

#### Scenario: Complete compaction
- **WHEN** a complete-history compact request contains foreign ciphertext even with a display summary
- **THEN** it fails explicitly without claiming the full provider state was preserved
- **AND** a plaintext-only history can compact with all its readable reasoning

#### Scenario: Mixed-provider round trip
- **WHEN** completed Claude signed state and readable OpenAI history are replayed to their authorized original Claude model/account
- **THEN** genuine Claude blocks remain verbatim and only foreign readable reasoning becomes text

#### Scenario: Fork or tampering
- **WHEN** a Claude envelope has a foreign client/conversation scope or invalid authentication
- **THEN** invalid_provider_history identifies the input index before upstream dispatch without weakening scope checks
