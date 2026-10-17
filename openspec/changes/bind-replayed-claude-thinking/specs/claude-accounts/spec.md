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
