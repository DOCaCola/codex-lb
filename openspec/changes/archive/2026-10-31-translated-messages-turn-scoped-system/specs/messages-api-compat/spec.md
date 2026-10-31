## ADDED Requirements

### Requirement: Messages turn-scoped system messages

A message-level system message with `clear_at: "next_user_message"` SHALL be translated only while no
`role: "user"` message follows it in `messages`; once a later user message exists, including one carrying only tool
results, the translator SHALL omit it from the input. System messages without `clear_at` or with
`clear_at: "never"` SHALL be translated on every request. A `clear_at` value other than `"next_user_message"` or
`"never"` SHALL fail before dispatch with `invalid_request_error`.

#### Scenario: Current-turn reminder
- **WHEN** a turn-scoped system message follows the last user message
- **THEN** upstream receives it as a developer message

#### Scenario: Expired reminder
- **WHEN** a later user message, or a user message carrying only tool results, follows a turn-scoped system message
- **THEN** upstream does not receive the turn-scoped message

#### Scenario: Permanent system message
- **WHEN** a system message has `clear_at: "never"` and later user messages follow it
- **THEN** upstream receives it as a developer message

#### Scenario: Unknown scope
- **WHEN** a system message carries an unrecognised `clear_at` value
- **THEN** it fails before dispatch with `invalid_request_error`
