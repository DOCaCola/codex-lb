## ADDED Requirements

### Requirement: Messages mid-conversation tool changes

Message-level system content MAY carry `tool_addition` and `tool_removal` blocks alongside text. The translator
SHALL apply them in message order to the request's tool catalog, which starts as the top-level declarations: an
addition with a `tool_definition` declares the named tool or replaces its declaration; an addition with a
`tool_reference` re-offers a tool declared earlier in the request; a removal with a `tool_reference` withdraws the
named tool. Upstream SHALL receive the resulting catalog as top-level tools, in first-declaration order, translated
like top-level declarations, with names longer than 64 characters aliased and restored in the output. Tool changes
SHALL NOT produce input items; text in the same system message SHALL be translated as before.

A reference to a tool not declared earlier in the request, a tool change in a system message whose `clear_at` is
other than `never`, and a top-level tool name declared more than once SHALL fail before dispatch with
`invalid_request_error`.

#### Scenario: Inline MCP tool added late
- **WHEN** a system message after earlier turns adds an inline definition for an MCP tool
- **THEN** upstream receives the top-level tools followed by the added tool, and no input item for the change

#### Scenario: Deferred tool removed and re-offered
- **WHEN** a system message withdraws a top-level tool and a later one re-offers it by reference
- **THEN** upstream receives the tool at its original position

#### Scenario: Removed tool
- **WHEN** a system message withdraws a top-level tool
- **THEN** upstream does not receive that tool, while earlier calls to it remain in the history

#### Scenario: Long inline tool name
- **WHEN** an inline definition names a tool longer than 64 characters and the model calls it
- **THEN** upstream receives the alias and the client receives the original name

#### Scenario: Unknown reference
- **WHEN** a tool change references a tool the request never declared
- **THEN** it fails before dispatch with `invalid_request_error` naming the tool

#### Scenario: Turn-scoped tool change
- **WHEN** a system message with `clear_at: "next_user_message"` carries a tool addition
- **THEN** it fails before dispatch with `invalid_request_error`
