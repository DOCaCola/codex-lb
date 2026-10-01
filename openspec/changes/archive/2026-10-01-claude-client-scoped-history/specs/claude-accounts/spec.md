## MODIFIED Requirements

### Requirement: Translated hosted web search
Translated Claude Responses SHALL accept nameless web_search declarations and map supported live search options to native Anthropic search. A declaration with external_web_access=false SHALL be omitted, allowing conversation to continue without granting cached or live search through that tool. Other unsupported options MUST fail before dispatch rather than silently weaken caller constraints. HTTP and WebSocket Responses SHALL expose search lifecycle and URL citations, preserve real upstream search state across continuation, and reject missing, tampered or cross-account/model/client replay state. Server search errors and unfinished searches MUST NOT become successful completion.

#### Scenario: Default Codex search declaration
- **WHEN** Codex includes a nameless live web_search tool
- **THEN** the request reaches Claude as a versioned server-search declaration instead of failing name validation

#### Scenario: Cached-only search
- **WHEN** Codex includes web_search with external_web_access=false
- **THEN** the declaration is omitted and the remaining conversation and tools proceed without enabling live search

#### Scenario: Search continuation
- **WHEN** a client replays search output with its authenticated opaque state
- **THEN** the exact upstream search blocks are restored under the same authorized owner

#### Scenario: Missing search state
- **WHEN** a search output has no matching authenticated opaque state
- **THEN** preparation fails explicitly without dispatch

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against the client scope before routing. Conversation identity SHALL govern session identity, routing affinity and retained continuation but MUST NOT authorize history, so a forked or other conversation of the same client SHALL replay authenticated state under the same model and account ownership rules. Completed thinking SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking from outbound projection while preserving visible text and paired tools and leaving retained history unchanged; compaction SHALL instead project completed thinking as readable historical assistant text and omit only redacted thinking. It SHALL record conversion and omission counts without content or credentials. Active reasoning and server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking completed; compaction SHALL determine this on the client-supplied history excluding its summarization instruction. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Compaction on another route
- **WHEN** compaction selects another account or model than completed thinking
- **THEN** the summarizer receives that thinking as readable assistant text in its original position, without a signature

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active reasoning

#### Scenario: Authenticated Chat tool cycle
- **WHEN** a keyed Chat client resends the complete visible history and all tool results for one live Claude tool response
- **THEN** the gateway restores only that response's genuine signed or redacted thinking under the same client, model and account owner
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client
- **THEN** preparation fails before upstream dispatch

#### Scenario: Forked conversation
- **WHEN** a forked conversation of the same client replays genuine envelopes minted under its parent conversation
- **THEN** authentication succeeds without fork metadata, completed thinking keeps only its account preference, and active reasoning and search keep their original model and account owner

### Requirement: Native resource provenance
Native server-tool history SHALL resolve its authorized source from observed
resource origins, independently of soft session affinity. Origins SHALL be
scoped to client and model, retained for thirty days of authorized
use, and persisted before output exposing the identifier. Unknown, expired or
conflicting origins SHALL fail explicitly without inferring ownership from
affinity or incoming history. Ordinary tools and translated replay SHALL retain
their existing contracts. Count-token requests SHALL NOT create or extend origins.
Unsupported native file/container resource references SHALL fail explicitly.

#### Scenario: Affinity expires
- **WHEN** native history replays a retained resource after affinity expires
- **THEN** the request selects the resource's authorized origin account

#### Scenario: Branch rebinds
- **WHEN** different branches obtain resources on different accounts
- **THEN** each resource resolves independently and mixed-origin history fails

#### Scenario: Forked native session
- **WHEN** a forked native session of the same client replays a retained server resource
- **THEN** the request selects the resource's original origin account

#### Scenario: Persistence fails
- **WHEN** a new resource origin cannot be committed
- **THEN** its identifying output is not delivered and generation is not retried

### Requirement: Claude history at native Codex dispatch

Native Codex dispatch SHALL authenticate replayed Claude envelopes against the originating client before projecting history. Readable Claude thinking SHALL become portable reasoning summary text without forwarding Claude encryption, signatures or foreign lookup identities. Existing summaries and distinct plaintext reasoning SHALL be preserved. Projection SHALL leave retained logical history, messages, tool call identifiers and paired outputs unchanged. The same policy SHALL apply to HTTP, WebSocket, retained continuation and native compaction.

Native sanitation SHALL remove invalid known item-type ID prefixes without fabricating identities, preserve valid native opaque reasoning and reject unprojected Claude envelopes. Redacted thinking and Claude-hosted search/resource state SHALL fail before dispatch with `nonportable_provider_history` and an input path instead of being silently deleted or treated as native state. Authentication failures MUST NOT dispatch or penalize an upstream account.

#### Scenario: Opus-to-Sol switch
- **WHEN** a scoped Claude thinking envelope with empty summary and a resp_msg-prefixed reasoning ID is replayed to native Sol
- **THEN** its readable text becomes summary_text and neither its Claude envelope nor foreign ID reaches OpenAI
- **AND** the original retained item remains unchanged

#### Scenario: Tool continuation
- **WHEN** readable Claude thinking accompanies a complete function/custom-tool call and result pair
- **THEN** native projection preserves their identifiers, arguments and outputs in order

#### Scenario: Tampered or cross-scope envelope
- **WHEN** Claude state is invalid or belongs to another client
- **THEN** the native request fails before upstream dispatch without exposing state contents

#### Scenario: Unrepresentable provider state
- **WHEN** native input contains authenticated redacted thinking or Claude-hosted search state
- **THEN** it returns nonportable_provider_history at the affected input index and retains the original data

#### Scenario: Native history stays native
- **WHEN** native reasoning with valid rs-prefixed identity and encrypted content is replayed
- **THEN** its encryption remains intact and no Claude projection occurs

#### Scenario: Plaintext reasoning preservation
- **WHEN** a reasoning item carries both an existing summary and distinct reasoning_text content
- **THEN** native sanitation retains both texts as summaries and empties the content array

### Requirement: Foreign reasoning at Claude dispatch

Translated Claude Responses SHALL classify provider-specific reasoning before signed-history authentication and account selection. Completed foreign reasoning with readable summary or reasoning_text content SHALL become ordinary historical assistant text, preserving distinct text and ordering without ciphertext, lookup IDs or fabricated thinking signatures. Completed foreign encrypted reasoning without readable text SHALL produce no Claude wire block, without blocking the surrounding portable conversation. Plaintext-only reasoning SHALL follow the same portable projection. Logical retained history, user/assistant messages and tool pairing MUST remain unchanged. Input positions SHALL remain stable for indexed diagnostics. The policy SHALL apply after expansion to HTTP and WebSocket, including replayed continuation.

Foreign encrypted reasoning in the active turn MUST fail before dispatch with nonportable_provider_history and the affected input index. A paired tool output MUST NOT count as a new user turn. Complete-history compaction SHALL apply the same rule to the client-supplied history, excluding its summarization instruction: a history ending with an assistant message is a closed turn with no active reasoning; otherwise the active turn starts at the last user or external task input. Purely plaintext compaction SHALL preserve all readable reasoning. Genuine Claude envelopes, including empty-display signed blocks, MUST retain existing client authentication and account/model ownership. Authentication failures SHALL expose invalid_provider_history with an input index rather than a generic payload message. Conversion and opaque-omission diagnostics MUST contain counts only, never reasoning or opaque contents.

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
- **WHEN** a Claude envelope minted in a parent conversation of the same client is replayed by a fork
- **THEN** it authenticates and dispatch follows the normal model and account ownership rules
- **AND** an envelope with a foreign client scope or invalid authentication returns invalid_provider_history identifying the original input index before upstream dispatch
