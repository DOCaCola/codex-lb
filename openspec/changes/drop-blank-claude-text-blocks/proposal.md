# Drop Blank Text From Translated Claude Requests

## Why

Anthropic rejects a Messages request containing an empty or whitespace-only text block ("text content blocks must
be non-empty") and a message without content. Codex replays such content: empty user messages, an empty text part
before a tool call, and tool output without visible content (OpenCodex `7ff4c7c4e`). The Responses projection
forwarded every text part unchanged, so one blank part failed the whole request. CLIProxyAPI `df07b1e` (#6820) fixed
the same defect by dropping blank text parts at translation time; its empty tool output has long been sent as an empty
string. Production shows no occurrence in the last 30 days; this closes the gap before a client produces one.

## What Changes

- Translated content drops text parts that are empty or contain only whitespace; this covers messages, tool outputs,
  external task input, standalone outputs and code-mode notifications.
- A user or assistant message left without content is omitted. A blank user message does not interrupt a pending
  tool call.
- A paired tool output without visible content becomes a `tool_result` with empty string content; a later code-mode
  notification replaces it.
- Whitespace-only instructions and reasoning summary text are not projected.
- Gateway cache breakpoints therefore never land on a blank text block. Native Messages requests are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: adds "Translated Claude requests carry no blank text".

## Impact

- `app/modules/claude/protocol.py` (`_content`, message, tool output, notification, summary and instruction
  projection).
- The model no longer sees blank parts it could not use; OpenCodex's placeholder text is not adopted, because it
  would add content the client never sent.
