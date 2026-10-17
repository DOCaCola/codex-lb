## ADDED Requirements

### Requirement: Preserved-thinking prefix binding
A Messages or token-counting request to Opus 5.5, Sonnet 5.5, Haiku 5.5 or Fable 5.1 (dated snapshots included) that
replays a signed `thinking` block or a `redacted_thinking` block SHALL default
`thinking.block_binding.prefix_mismatch_behavior` to `drop_block` when its thinking mode accepts a binding: adaptive
thinking for every listed model, and manual `enabled` thinking for Opus 5.5 and Fable 5.1 only. A caller-supplied
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

### Requirement: Thinking binding reports are logged
When a Claude Messages response reports a non-empty `input_transformations` list, in a streaming `message_start` or
a non-streaming response, the gateway SHALL log one `claude_thinking_binding` line with the conversation, serving
account, entry counts by type and reason as reported (including types it does not recognize), and the first reported
path. When the conversation, or for a forked side chat its parent session, has a previous observed request, the line
SHALL also name whether the account changed, the idle time, tool, system and parameter changes, message counts and the
first diverging message. The line MUST NOT contain message content, reasoning or signatures. An empty list SHALL NOT
be logged.

#### Scenario: Blocks dropped after an account move
- **WHEN** a continuation served by another account reports two `thinking_dropped` entries
- **THEN** one line reports `thinking_dropped:prefix_binding_mismatch:2`, the first path and `same_source=False`

#### Scenario: Nothing to report
- **WHEN** `input_transformations` is empty or absent
- **THEN** no binding line is logged
