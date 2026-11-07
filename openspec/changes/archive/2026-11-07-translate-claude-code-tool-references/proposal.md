# Translate Claude Code tool references

## Why

With `ENABLE_TOOL_SEARCH=true`, Claude Code declares tools with
`defer_loading` and its ToolSearch tool returns each loaded tool as a
`tool_reference` block in the tool result. Translated Messages requests for
OpenAI, OpenRouter and Antigravity models rejected that block with a 400, so a
session switched from a Claude model to one of those failed at its first tool
search. Responses has no carrier for the block.

opencodex renders each reference as `Tool loaded: <name>` text (#6647, after
a reference-only result became empty); CLIProxyAPI drops the block silently.

## What Changes

- Each `tool_reference` in a translated tool result becomes its own text
  line `Tool loaded: <name>`, in content order, naming the tool as the
  translated request declares it (aliased above 64 characters).
- Markers carry their own line breaks, because some adapters join tool-output
  text parts without separators.
- A reference without a tool name is rejected.
- Deferred tools stay ordinary functions, so a reference grants nothing.
  Native Claude passthrough is unchanged.

## Impact

Messages request translation only. Not verified against a live Claude Code
session with tool search enabled.
