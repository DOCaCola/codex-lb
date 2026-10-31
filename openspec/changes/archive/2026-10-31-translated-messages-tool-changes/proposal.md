## Why

Claude Code 2.1.314 changes its tool set mid-conversation instead of rewriting the top-level `tools` array: a
`role: "system"` message carries `tool_addition` blocks (an inline `tool_definition` or a `tool_reference` to a
deferred top-level tool) and `tool_removal` blocks (a `tool_reference`). Translated Messages requests to OpenAI,
OpenRouter and Antigravity models reject these system messages today, so Claude Code sessions that load MCP tools
late fail before dispatch.

CLIProxyAPI (12d97cf) emits a Responses `additional_tools` input item for each addition and ignores removals.
`additional_tools` belongs to the Responses Lite request shape, in which tools arrive only as input items and
instructions move into the input; translated requests use the standard shape with top-level `tools` and
`instructions`, and codex-lb marks any request carrying `additional_tools` as Responses Lite. agent-lb (f57da05)
instead applies additions and removals to the top-level tool set, which is also what Claude Code itself falls back
to when inline tools are refused. A changed tool set changes the prompt prefix from that request on, as it did
before Claude Code adopted tool changes.

## What Changes

- Message-level system content accepts `tool_addition` and `tool_removal` blocks alongside text.
- The translator applies them in message order to the request's tool catalog and sends the resulting catalog as
  top-level tools, translated and aliased like top-level declarations.
- References to undeclared tools, tool changes in turn-scoped (`clear_at` other than `never`) system messages and
  duplicate top-level tool names fail before dispatch with `invalid_request_error`, as Anthropic refuses them.

## Impact

- Affected specs: `messages-api-compat`
- Affected code: `app/core/messages/translate.py`
