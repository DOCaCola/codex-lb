## ADDED Requirements

### Requirement: Translated Claude progress updates
Translated Responses requests to Claude Opus 5.5, Fable 5.1, Mythos 5.1, Sonnet 5 or Sonnet 5.5, including dated
aliases, whose projected thinking is `adaptive` or `enabled` and whose caller chose no thinking display, SHALL send
`thinking.display: "updates"`. An explicit caller display SHALL be sent unchanged. Other models, disabled thinking and
native Messages MUST NOT receive the display from this rule. Any Claude request whose body carries
`display: "updates"` SHALL negotiate `thinking-display-updates-2026-08-18`.

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

#### Scenario: Model without progress updates
- **WHEN** a translated request targets Haiku 5.5
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
