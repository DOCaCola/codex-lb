## MODIFIED Requirements

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against client and conversation before routing. Completed thinking SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking from outbound projection while preserving visible text and paired tools and leaving retained history unchanged. It SHALL record an omission count without content or credentials. Active reasoning and server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking completed. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active reasoning

#### Scenario: Authenticated Chat tool cycle
- **WHEN** a keyed Chat client resends the complete visible history and all tool results for one live Claude tool response
- **THEN** the gateway restores only that response's genuine signed or redacted thinking under the same conversation, model and account owner
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client or conversation
- **THEN** preparation fails before upstream dispatch

## ADDED Requirements

### Requirement: Canonical Codex external task input
Translated Claude Responses over HTTP and WebSocket SHALL recognize a function_call_output as external task input only when its call_id is omitted, null or a blank string, its id/name/namespace are nonblank strings, and its output is nonblank text or a nonempty array containing only supported text/image blocks with nonblank text or an image. Image blocks SHALL have a nonblank image_url and, if supplied, a valid detail value (auto/low/high/original); the existing Claude image transport/media validation SHALL also apply. Wrong-typed call identifiers, incomplete metadata, blank content and unsupported blocks MUST NOT qualify. The complete output SHALL be preserved in order as ordinary user content without an orphan label, fabricated tool call or signed state. Logical history SHALL remain unchanged. External task input MUST NOT interrupt or satisfy pending tool calls.

#### Scenario: Task input within established history
- **WHEN** a complete external task envelope with null call_id follows completed assistant history
- **THEN** its entire text/image output is projected as new user input and retained logical history keeps the original envelope

#### Scenario: Malformed output cannot masquerade as task input
- **WHEN** an ID-less output lacks required metadata, contains unsupported content, or has a wrong-typed call identifier
- **THEN** it fails explicitly before upstream dispatch without discarding content or inventing pairing

#### Scenario: A task does not complete an active tool call
- **WHEN** canonical external task input arrives before pending tool calls receive their results
- **THEN** the request fails without discharging those calls

### Requirement: External task replay boundary
Canonical external task input SHALL count as a new user turn when classifying completed versus active signed thinking, using the same classifier as protocol projection. All opaque blocks MUST be authenticated before omission. Tool results and malformed task envelopes MUST NOT close active thinking. Server search/resource state SHALL retain its existing strict account/model ownership. Rejected tool-output diagnostics SHALL include identifier presence/type and metadata completeness without raw metadata or content.

#### Scenario: Completed thinking before a new task
- **WHEN** authenticated thinking precedes canonical external task input and the target account/model changes
- **THEN** only completed thinking may be omitted under the existing replay policy, and task content remains intact

#### Scenario: Search ownership is not relaxed by a task
- **WHEN** canonical external task input follows account-bound search history
- **THEN** its search state still requires the original owner and model
