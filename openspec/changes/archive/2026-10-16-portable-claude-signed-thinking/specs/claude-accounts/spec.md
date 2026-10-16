## MODIFIED Requirements

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against the client scope before routing. Conversation identity SHALL govern session identity, routing affinity and retained continuation but MUST NOT authorize history, so a forked or other conversation of the same client SHALL replay authenticated state under the same rules. Authenticated signed and redacted thinking SHALL be forwarded verbatim to the selected Claude account and model, whichever produced it, in completed and active turns alike; Anthropic drops blocks the target cannot read. Thinking SHALL provide only a preferred eligible account, the producer of the latest authenticated block. Completed server search SHALL provide only a preferred eligible account; when the selected account or model differs, the gateway SHALL project it as portable hosted-search history, while preserving visible text and paired tools and leaving retained history unchanged. Compaction SHALL instead project completed thinking produced on another account or model as readable historical assistant text, omit such redacted thinking and project completed search the same way, while forwarding all other thinking verbatim. It SHALL record conversion, omission and search-projection counts without content or credentials. Active server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking and search completed; compaction SHALL determine this on the client-supplied history excluding its summarization instruction. Invalid authentication, active search for another model and conflicting active search owners MUST fail before dispatch with code invalid_provider_history or nonportable_provider_history, the input index and their specific message.

#### Scenario: Historical account unavailable
- **WHEN** only thinking belongs to an unavailable account
- **THEN** an eligible alternative serves the conversation with that thinking forwarded verbatim

#### Scenario: Model switch
- **WHEN** completed or active thinking belongs to another Claude model
- **THEN** the requested model receives it verbatim, and switching back later keeps the history append-only

#### Scenario: Stopped tool turn resumed on another model
- **WHEN** the client stops a Claude tool loop, switches model and resumes without a new user message
- **THEN** the request is dispatched with the active signed thinking verbatim instead of failing before dispatch

#### Scenario: Completed search on another route
- **WHEN** completed server search belongs to another model or an unavailable account
- **THEN** the selected route receives the projected search text without the original call and encrypted result

#### Scenario: Compaction on another route
- **WHEN** compaction selects another account or model than completed thinking
- **THEN** the summarizer receives that thinking as readable assistant text in its original position, without a signature

#### Scenario: Active tool cycle
- **WHEN** server search belongs to the active tool turn and the selected model differs or its owner is unavailable
- **THEN** preparation fails with nonportable_provider_history or the owner-unavailable error rather than dropping required active state

#### Scenario: Authenticated Chat tool cycle
- **WHEN** a keyed Chat client resends the complete visible history and all tool results for one live Claude tool response
- **THEN** the gateway restores only that response's genuine signed or redacted thinking under the same client, model and account owner
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client
- **THEN** preparation fails before upstream dispatch with invalid_provider_history and the envelope's input index

#### Scenario: Forked conversation
- **WHEN** a forked conversation of the same client replays genuine envelopes minted under its parent conversation
- **THEN** authentication succeeds without fork metadata, thinking and completed search keep only their account preference, and active search keeps its original model and account owner

### Requirement: External task replay boundary
Canonical external task input SHALL count as a new user turn when classifying completed versus active signed thinking and server search, using the same classifier as protocol projection. All opaque blocks MUST be authenticated before conversion or projection. Tool results and malformed task envelopes MUST NOT close active thinking or search. Server resource state SHALL retain its existing strict account/model ownership. Rejected tool-output diagnostics SHALL include identifier presence/type and metadata completeness without raw metadata or content.

#### Scenario: Completed thinking before a new task
- **WHEN** authenticated thinking precedes canonical external task input and compaction runs on another account or model
- **THEN** that thinking is completed and becomes readable assistant text, and task content remains intact

#### Scenario: Search ownership is not relaxed by a task
- **WHEN** canonical external task input follows Claude search history and the target account/model changes
- **THEN** that search is completed and is projected as portable hosted-search history
- **AND** its call and encrypted result are still sent only to their original owner and model

#### Scenario: Search inside an active tool cycle
- **WHEN** Claude search belongs to a turn that only paired tool output follows
- **THEN** it still requires the original owner and model on another Claude route

### Requirement: Foreign reasoning at Claude dispatch

Translated Claude Responses SHALL classify provider-specific reasoning before signed-history authentication and account selection. Foreign reasoning with readable summary or reasoning_text content SHALL become ordinary assistant text, preserving distinct text and ordering without ciphertext, lookup IDs or fabricated thinking signatures. Foreign encrypted reasoning without readable text SHALL produce no Claude wire block, without blocking the surrounding portable conversation. Plaintext-only reasoning SHALL follow the same portable projection. This projection SHALL apply equally to completed turns and the active turn, including an open tool loop. Logical retained history, user/assistant messages and tool pairing MUST remain unchanged. Input positions SHALL remain stable for indexed diagnostics. The policy SHALL apply after expansion to HTTP and WebSocket, including replayed continuation.

A paired tool output MUST NOT count as a new user turn. Complete-history compaction SHALL project the client-supplied history the same way, excluding its summarization instruction. Genuine Claude envelopes, including empty-display signed blocks, MUST retain client authentication and the signed-history replay rules. Authentication failures SHALL expose invalid_provider_history with an input index rather than a generic payload message. Projection diagnostics MUST contain counts only, including how many projected items belong to the active turn, never reasoning or opaque contents.

#### Scenario: Sol-to-Opus historical switch
- **WHEN** completed OpenAI reasoning has a readable summary and encrypted_content before a new user message
- **THEN** Claude receives the summary as historical assistant text, no foreign ciphertext or synthetic thinking, and retained history remains unchanged

#### Scenario: Opaque-only history
- **WHEN** completed foreign encrypted reasoning has no readable summary or content
- **THEN** Claude receives the surrounding portable messages and tool pairs without that private reasoning block
- **AND** retained history keeps its original ciphertext and item ordering for native replay

#### Scenario: Active foreign tool continuation
- **WHEN** foreign encrypted reasoning belongs to the active assistant turn and is followed only by paired tool output
- **THEN** Claude receives its readable text, the tool call and the tool result without foreign ciphertext or synthetic thinking
- **AND** the projection log counts the item as active

#### Scenario: Complete compaction
- **WHEN** a Claude compact request contains foreign encrypted reasoning before the last user input, or in a closed turn ending with an assistant message
- **THEN** it summarizes the readable conversation without foreign ciphertext, exactly as a normal turn would project it

#### Scenario: Compaction inside an open foreign tool loop
- **WHEN** a Claude compact request ends in tool output of a turn whose foreign encrypted reasoning follows the last user input
- **THEN** it summarizes the readable conversation without foreign ciphertext, exactly as a normal turn would project it
- **AND** a plaintext-only history can compact with all its readable reasoning

#### Scenario: Mixed-provider round trip
- **WHEN** completed Claude signed state and readable or opaque-only OpenAI history are replayed to a Claude model/account
- **THEN** genuine Claude blocks remain verbatim, foreign readable reasoning becomes text, and opaque-only foreign state produces no Claude block

#### Scenario: Fork or tampering
- **WHEN** a Claude envelope minted in a parent conversation of the same client is replayed by a fork
- **THEN** it authenticates and dispatch follows the normal signed-history replay rules
- **AND** an envelope with a foreign client scope or invalid authentication returns invalid_provider_history identifying the original input index before upstream dispatch
