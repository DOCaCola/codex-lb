# Tasks

## 1. Implementation

- [x] 1.1 Drop empty and whitespace-only text parts in the Responses content projection.
- [x] 1.2 Omit user and assistant messages without remaining content, before the pending tool-call check.
- [x] 1.3 Project a paired tool output without visible content as empty string `tool_result` content; let a code-mode
  notification replace it.
- [x] 1.4 Skip whitespace-only instructions and reasoning summary text.

## 2. Verification

- [x] 2.1 Unit tests for blank messages, parts, instructions, summaries, tool outputs, standalone outputs, external task
  input and code-mode notifications.
- [x] 2.2 Full test suite and `openspec validate --strict`.
