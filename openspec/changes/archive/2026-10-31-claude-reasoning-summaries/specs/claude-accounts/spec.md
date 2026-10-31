## MODIFIED Requirements

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
- **WHEN** compaction projects history with a presented update produced on another account as readable text
- **THEN** the update text appears once, carried by its commentary copy

## ADDED Requirements

### Requirement: Translated Claude reasoning summaries
Translated Responses requests SHALL accept `reasoning.summary` values `auto`, `concise`, `detailed` and `none`, and
MUST reject any other value before dispatch. When the caller chose no thinking display and the projected thinking is
`adaptive`, the gateway SHALL send `thinking.display: "summarized"` for a `concise` or `detailed` summary on
progress-update models, and for any summary other than `none` on other models.

When a summary other than `none` is requested, the caller did not choose `omitted` and the projected display is not
`updates`, each signed `thinking` block SHALL stream as a reasoning item whose summary carries the block's readable
text: `response.reasoning_summary_part.added` when the block opens, `response.reasoning_summary_text.delta` per text
delta, then `response.reasoning_summary_text.done` and `response.reasoning_summary_part.done` before the item's done
event. The authenticated opaque state SHALL be unchanged. Chat Completions reasoning SHALL keep its existing visibility.

#### Scenario: Detailed summary on Opus 5.5
- **WHEN** a Responses request for Opus 5.5 carries `reasoning.summary: "detailed"`
- **THEN** Claude receives `display: "summarized"` without the updates beta and the client receives the thinking
  text as the reasoning item's summary

#### Scenario: Default summary on an adaptive model without progress updates
- **WHEN** a Responses request for Haiku 5.5 with adaptive thinking carries `reasoning.summary: "auto"`
- **THEN** Claude receives `display: "summarized"` and the client receives the thinking text as a summary

#### Scenario: Summaries disabled
- **WHEN** a Responses request carries `reasoning.summary: "none"`
- **THEN** no summarized display is requested and reasoning items keep an empty summary

#### Scenario: Unknown summary value
- **WHEN** a Responses request carries `reasoning.summary: "verbose"`
- **THEN** the request is rejected before dispatch with param `reasoning.summary`
