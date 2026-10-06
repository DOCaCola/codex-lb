## ADDED Requirements

### Requirement: Claude catalog models select multi-agent v2
Claude catalog models SHALL advertise `multi_agent_version` `"v2"`, so agent trees rooted on a Claude model use Codex's message-based subagent protocol.

#### Scenario: Claude model in the Codex catalog
- **WHEN** a client lists models and a Claude source model is enabled
- **THEN** its entry carries `multi_agent_version: "v2"`

#### Scenario: Other model sources
- **WHEN** an OpenRouter or OpenAI-compatible source model is listed
- **THEN** its entry carries no `multi_agent_version` from codex-lb

### Requirement: Portable hosted-search history
Hosted-search history that cannot be replayed natively on the destination route SHALL be projected as readable historical assistant text instead of failing. The projection SHALL replace the search call, and any search-state carrier, with one assistant `output_text` message at the call's position. The message SHALL contain the search action — `Web search: <query>`, `Opened page: <url>` or `Found in page <url>: <pattern>` — followed, when result entries are available, by `Sources:` and one `<title> — <url>` line per result. Claude results SHALL supply title and URL from `web_search_result` entries. OpenAI results SHALL supply them from `action.sources` when present.

The rendering SHALL be deterministic for identical history. It MUST NOT include encrypted result content, signatures, provider item identities or page text. It MUST NOT fabricate a search call, encrypted result or server-resource ownership. Retained logical history SHALL keep the original items. Projection diagnostics SHALL count projected searches without content.

The projection SHALL apply to:

- Claude hosted search sent to native OpenAI, in completed and active turns.
- OpenAI `web_search_call` items sent to Claude, in completed and active turns.
- Completed Claude hosted search sent to a different Claude model or account.

#### Scenario: Claude search in a GPT child
- **WHEN** a forked child on native OpenAI replays its Claude parent's completed hosted search
- **THEN** OpenAI receives the query and result titles and URLs as assistant text, and no Claude envelope, `web_search_call` or foreign identity

#### Scenario: OpenAI search in a Claude child
- **WHEN** a Claude request contains an OpenAI `web_search_call` with `action.sources`
- **THEN** Claude receives the query and sources as assistant text, and the request does not fail for missing Claude search state

#### Scenario: OpenAI search without sources
- **WHEN** an OpenAI `web_search_call` has no `action.sources`
- **THEN** Claude receives only the search action line

#### Scenario: Claude search on another Claude model
- **WHEN** completed Claude hosted search belongs to another model or account than the selected route
- **THEN** the selected model receives the projected text and the original call and result blocks are not sent

#### Scenario: Original route
- **WHEN** the conversation later returns to the search's original Claude model and account
- **THEN** the retained call and encrypted result replay natively

## MODIFIED Requirements

### Requirement: Claude history at native Codex dispatch

Native Codex dispatch SHALL authenticate replayed Claude envelopes against the originating client before projecting history. Readable Claude thinking SHALL become portable reasoning summary text without forwarding Claude encryption, signatures or foreign lookup identities. Existing summaries and distinct plaintext reasoning SHALL be preserved. Projection SHALL leave retained logical history, messages, tool call identifiers and paired outputs unchanged. The same policy SHALL apply to HTTP, WebSocket, retained continuation and native compaction.

Native sanitation SHALL remove invalid known item-type ID prefixes without fabricating identities, preserve valid native opaque reasoning and reject unprojected Claude envelopes. Authenticated redacted thinking SHALL be omitted, because it has no readable content or native representation. Authenticated Claude-hosted search SHALL follow portable hosted-search history projection. Both SHALL apply in completed and active turns. Projection diagnostics SHALL count converted thinking, omitted redacted thinking and projected searches without content. Authentication failures MUST NOT dispatch or penalize an upstream account.

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
- **WHEN** native input contains authenticated Claude redacted thinking
- **THEN** OpenAI receives the surrounding history without that item, the omission is counted, and retained history keeps the original

#### Scenario: Claude hosted search
- **WHEN** native input contains an authenticated Claude search envelope and its `web_search_call`
- **THEN** OpenAI receives one projected assistant text message in their place, and neither the envelope nor the Claude call identity

#### Scenario: Native history stays native
- **WHEN** native reasoning with valid rs-prefixed identity and encrypted content is replayed
- **THEN** its encryption remains intact and no Claude projection occurs

#### Scenario: Plaintext reasoning preservation
- **WHEN** a reasoning item carries both an existing summary and distinct reasoning_text content
- **THEN** native sanitation retains both texts as summaries and empties the content array

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against the client scope before routing. Conversation identity SHALL govern session identity, routing affinity and retained continuation but MUST NOT authorize history, so a forked or other conversation of the same client SHALL replay authenticated state under the same model and account ownership rules. Completed thinking and completed server search SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking and project incompatible completed search as portable hosted-search history, while preserving visible text and paired tools and leaving retained history unchanged. Compaction SHALL instead project completed thinking as readable historical assistant text, omit only redacted thinking and project completed search the same way. It SHALL record conversion, omission and search-projection counts without content or credentials. Active reasoning and active server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking and search completed; compaction SHALL determine this on the client-supplied history excluding its summarization instruction. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Completed search on another route
- **WHEN** completed server search belongs to another model or an unavailable account
- **THEN** the selected route receives the projected search text without the original call and encrypted result

#### Scenario: Compaction on another route
- **WHEN** compaction selects another account or model than completed thinking
- **THEN** the summarizer receives that thinking as readable assistant text in its original position, without a signature

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning or server search belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active state

#### Scenario: Authenticated Chat tool cycle
- **WHEN** a keyed Chat client resends the complete visible history and all tool results for one live Claude tool response
- **THEN** the gateway restores only that response's genuine signed or redacted thinking under the same client, model and account owner
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client
- **THEN** preparation fails before upstream dispatch

#### Scenario: Forked conversation
- **WHEN** a forked conversation of the same client replays genuine envelopes minted under its parent conversation
- **THEN** authentication succeeds without fork metadata, completed thinking and search keep only their account preference, and active reasoning and search keep their original model and account owner

### Requirement: External task replay boundary
Canonical external task input SHALL count as a new user turn when classifying completed versus active signed thinking and server search, using the same classifier as protocol projection. All opaque blocks MUST be authenticated before omission or projection. Tool results and malformed task envelopes MUST NOT close active thinking or search. Server resource state SHALL retain its existing strict account/model ownership. Rejected tool-output diagnostics SHALL include identifier presence/type and metadata completeness without raw metadata or content.

#### Scenario: Completed thinking before a new task
- **WHEN** authenticated thinking precedes canonical external task input and the target account/model changes
- **THEN** only completed thinking may be omitted under the existing replay policy, and task content remains intact

#### Scenario: Search ownership is not relaxed by a task
- **WHEN** canonical external task input follows Claude search history and the target account/model changes
- **THEN** that search is completed and is projected as portable hosted-search history
- **AND** its call and encrypted result are still sent only to their original owner and model

#### Scenario: Search inside an active tool cycle
- **WHEN** Claude search belongs to a turn that only paired tool output follows
- **THEN** it still requires the original owner and model on another Claude route

### Requirement: Inter-agent messages are Claude user turns
Translated Claude Responses requests SHALL accept `agent_message` items whose content is plaintext and project them as user turns, under the same tool-cycle rules as user messages. The turn SHALL carry the item's content unchanged; Codex's agent-message header naming the recipient and sender is part of that content, and the proxy MUST NOT add another. An `agent_message` with an `encrypted_content` part SHALL fail with `nonportable_agent_message` and SHALL NOT be dropped or forwarded as text.

#### Scenario: Child progress wakes a Claude parent
- **WHEN** a Claude parent's history contains a plaintext `agent_message` from its child after a completed tool cycle
- **THEN** Claude receives the message content, including Codex's header, exactly once as a user turn

#### Scenario: Pre-deployment encrypted message
- **WHEN** the history contains an `agent_message` with OpenAI ciphertext
- **THEN** the request fails with `nonportable_agent_message`
