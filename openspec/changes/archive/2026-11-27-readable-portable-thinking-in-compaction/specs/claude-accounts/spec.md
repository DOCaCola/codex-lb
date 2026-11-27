## MODIFIED Requirements

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against the client scope before routing. Conversation identity SHALL govern session identity, routing affinity and retained continuation but MUST NOT authorize history, so a forked or other conversation of the same client SHALL replay authenticated state under the same rules. Authenticated signed and redacted thinking SHALL be forwarded verbatim to the selected Claude account and model, whichever produced it, in completed and active turns alike; Anthropic drops blocks the target cannot read. Thinking SHALL provide only a preferred eligible account, the producer of the latest authenticated block. Completed server search SHALL provide only a preferred eligible account; when the selected account or model differs, the gateway SHALL project it as portable hosted-search history, while preserving visible text and paired tools and leaving retained history unchanged. Compaction SHALL instead project completed thinking the selected route cannot read as readable historical assistant text: thinking produced by another model, or by Sonnet 5.5 or Haiku 5.5, including dated aliases, on another account or account identity generation. It SHALL omit such redacted thinking and project completed search the same way, while forwarding all other thinking verbatim, so readable thinking keeps the cached prefix and the binding of later signed blocks. It SHALL record conversion, omission and search-projection counts without content or credentials. Active server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking and search completed; compaction SHALL determine this on the client-supplied history excluding its summarization instruction. Invalid authentication, active search for another model and conflicting active search owners MUST fail before dispatch with code invalid_provider_history or nonportable_provider_history, the input index and their specific message.

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
- **WHEN** compaction selects another model than completed thinking, or another account for Sonnet 5.5 or Haiku 5.5 thinking
- **THEN** the summarizer receives that thinking as readable assistant text in its original position, without a signature

#### Scenario: Compaction of portable thinking on another account
- **WHEN** compaction selects another account for completed thinking of the same model, and that model is not Sonnet 5.5 or Haiku 5.5
- **THEN** the summarizer receives the signed thinking verbatim, and the request keeps the cached prefix of the preceding turns

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
- **WHEN** authenticated thinking precedes canonical external task input and compaction runs on a route that cannot read it
- **THEN** that thinking is completed and becomes readable assistant text, and task content remains intact

#### Scenario: Search ownership is not relaxed by a task
- **WHEN** canonical external task input follows Claude search history and the target account/model changes
- **THEN** that search is completed and is projected as portable hosted-search history
- **AND** its call and encrypted result are still sent only to their original owner and model

#### Scenario: Search inside an active tool cycle
- **WHEN** Claude search belongs to a turn that only paired tool output follows
- **THEN** it still requires the original owner and model on another Claude route

### Requirement: Translated Claude progress updates
Translated Responses requests to Claude Opus 5.5, Fable 5.1, Mythos 5.1, Sonnet 5 or Sonnet 5.5, including dated
aliases, whose projected thinking is `adaptive` or `enabled`, whose caller chose no thinking display and whose
`reasoning.summary` is absent, `auto` or `none`, SHALL send `thinking.display: "updates"`. An explicit caller
display SHALL be sent unchanged. Other models, disabled thinking and native Messages MUST NOT receive the display
from this rule. Any Claude request whose body carries `display: "updates"` SHALL negotiate
`thinking-display-updates-2026-08-18`.

Under `updates`, a completed signed `thinking` block with non-empty text SHALL be delivered as a reasoning item with an
empty summary whose authenticated opaque state holds the unchanged block marked as presented, followed by a separate
done assistant message with phase `commentary` whose text equals the block's text. Neither the commentary message nor
the reasoning item's done event SHALL be emitted before the block completes. The message MUST NOT join another message.

Replay SHALL restore a presented block in its original position and consume the immediately following assistant
message with phase `commentary` or no phase whose text equals the block's text exactly, with or without a message ID.
Any other following item SHALL be replayed as sent. Readable projections SHALL NOT convert a presented block whose copy
is present, so the update text appears once. The translated stop diagnostic SHALL log the number of progress updates
delivered, never their content.

#### Scenario: Steering answered in a progress update
- **WHEN** Opus 5.5 answers a mid-turn user message with a progress update before its next tool call
- **THEN** the Codex client receives a reasoning item with an empty summary, then a visible commentary message with
  the update text, then the tool call

#### Scenario: Caller-chosen display
- **WHEN** a Responses request for Opus 5.5 asks for `summarized` reasoning display
- **THEN** Claude receives `display: "summarized"` without the updates beta

#### Scenario: Default Codex summary keeps progress updates
- **WHEN** a Responses request for Opus 5.5 carries `reasoning.summary: "auto"`
- **THEN** Claude receives `display: "updates"` with the updates beta

#### Scenario: Model without progress updates
- **WHEN** a translated request targets Haiku 5.5 without a reasoning summary
- **THEN** no thinking display or updates beta is added

#### Scenario: Exact replay
- **WHEN** a client replays the reasoning item and its unedited commentary copy
- **THEN** Claude receives the original signed block followed by the tool use, without the copy as text

#### Scenario: Edited copy
- **WHEN** the commentary copy's text differs from the signed block's text
- **THEN** the signed block is restored and the copy is replayed as ordinary assistant text

#### Scenario: Stream fails inside an update
- **WHEN** the Claude stream fails before the progress-update block completes
- **THEN** the client receives neither the carrier's done event nor the commentary copy

#### Scenario: Compaction across accounts
- **WHEN** compaction projects history with a presented Sonnet 5.5 update produced on another account as readable text
- **THEN** the update text appears once, carried by its commentary copy
