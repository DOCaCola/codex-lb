# Spec Delta

## MODIFIED Requirements

### Requirement: Foreign reasoning at Claude dispatch

Translated Claude Responses SHALL classify provider-specific reasoning before signed-history authentication and account selection. Completed foreign reasoning with readable summary or reasoning_text content SHALL become ordinary historical assistant text, preserving distinct text and ordering without ciphertext, lookup IDs or fabricated thinking signatures. Completed foreign encrypted reasoning without readable text SHALL produce no Claude wire block, without blocking the surrounding portable conversation. Plaintext-only reasoning SHALL follow the same portable projection. Logical retained history, user/assistant messages and tool pairing MUST remain unchanged. Input positions SHALL remain stable for indexed diagnostics. The policy SHALL apply after expansion to HTTP and WebSocket, including replayed continuation.

Foreign encrypted reasoning in the active turn MUST fail before dispatch with nonportable_provider_history and the affected input index. A paired tool output MUST NOT count as a new user turn. Complete-history compaction SHALL apply the same rule to the client-supplied history, excluding its summarization instruction: a history ending with an assistant message is a closed turn with no active reasoning; otherwise the active turn starts at the last user or external task input. Purely plaintext compaction SHALL preserve all readable reasoning. Genuine Claude envelopes, including empty-display signed blocks, MUST retain existing client/conversation authentication and account/model ownership. Authentication failures SHALL expose invalid_provider_history with an input index rather than a generic payload message. Conversion and opaque-omission diagnostics MUST contain counts only, never reasoning or opaque contents.

#### Scenario: Sol-to-Opus historical switch
- **WHEN** completed OpenAI reasoning has a readable summary and encrypted_content before a new user message
- **THEN** Claude receives the summary as historical assistant text, no foreign ciphertext or synthetic thinking, and retained history remains unchanged

#### Scenario: Opaque-only history
- **WHEN** completed foreign encrypted reasoning has no readable summary or content
- **THEN** Claude receives the surrounding portable messages and tool pairs without that private reasoning block
- **AND** retained history keeps its original ciphertext and item ordering for native replay

#### Scenario: Active foreign tool continuation
- **WHEN** foreign encrypted reasoning belongs to the active assistant turn and is followed only by paired tool output
- **THEN** preparation fails explicitly instead of fabricating a signed continuation

#### Scenario: Complete compaction
- **WHEN** a Claude compact request contains foreign encrypted reasoning before the last user input, or in a closed turn ending with an assistant message
- **THEN** it summarizes the readable conversation without foreign ciphertext, exactly as a normal turn would project it

#### Scenario: Compaction inside an open foreign tool loop
- **WHEN** a Claude compact request ends in tool output of a turn whose foreign encrypted reasoning follows the last user input
- **THEN** it fails with nonportable_provider_history at that input index without upstream dispatch
- **AND** a plaintext-only history can compact with all its readable reasoning

#### Scenario: Mixed-provider round trip
- **WHEN** completed Claude signed state and readable or opaque-only OpenAI history are replayed to their authorized original Claude model/account
- **THEN** genuine Claude blocks remain verbatim, foreign readable reasoning becomes text, and completed opaque-only foreign state produces no Claude block

#### Scenario: Fork or tampering
- **WHEN** a Claude envelope has a foreign client/conversation scope or invalid authentication
- **THEN** invalid_provider_history identifies the original input index before upstream dispatch without weakening scope checks
