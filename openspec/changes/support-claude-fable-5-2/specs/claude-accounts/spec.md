## MODIFIED Requirements

### Requirement: Preserved-thinking prefix binding
A Messages or token-counting request to Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1 or Fable 5.2 (dated snapshots included) that
replays a signed `thinking` block or a `redacted_thinking` block SHALL default
`thinking.block_binding.prefix_mismatch_behavior` to `drop_block` when its thinking mode accepts a binding: adaptive
thinking for every listed model, and manual `enabled` thinking for Opus 5.5, Fable 5.1 and Fable 5.2 only. A caller-supplied
behavior SHALL be kept, and requests without thinking or without signed history SHALL NOT receive a binding. Every
request whose body carries `thinking.block_binding` SHALL send the `thinking-binding-controls-2026-08-01` beta.

#### Scenario: Translated or native replay on a preserved-thinking model
- **WHEN** a request to Opus 5.5 with adaptive thinking replays a signed thinking block
- **THEN** the upstream body carries `drop_block` and the request sends the binding-controls beta

#### Scenario: Manual thinking on Haiku 5.5
- **WHEN** a Haiku 5.5 request with manual `enabled` thinking replays a signed thinking block
- **THEN** no binding is added

#### Scenario: Caller-chosen behavior
- **WHEN** the caller already set `prefix_mismatch_behavior`
- **THEN** its value is forwarded unchanged

### Requirement: Translated Claude progress updates
Translated Responses requests to Claude Opus 5.5, Fable 5.1, Fable 5.2, Mythos 5.1, Sonnet 5, Sonnet 5.5 or Haiku 5.5, including dated
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
- **WHEN** a translated request targets Opus 5 without a reasoning summary
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
- **WHEN** compaction projects history with a presented update produced on another account as readable text
- **THEN** the update text appears once, carried by its commentary copy
