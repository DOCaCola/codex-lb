## Placement
Normalization lives in `app/modules/claude/protocol.py` only. The shared
`normalize_tool_choice` also serves native OpenAI passthrough, whose payloads
and cache prefixes are forwarded unchanged; altering it there would change
native wire bytes.

## Policy
- A tool-choice object whose `type` is `auto`, `none` or `required` and has no
  other field is the corresponding directive. Any extra field is rejected.
- Directives map as before: `required` to Anthropic `any`; `auto` and `none`
  unchanged. Declarations are retained for `none` so history and the tools
  cache prefix stay stable.
- Anthropic's `none` choice carries only `type`; `parallel_tool_calls: false`
  adds `disable_parallel_tool_use` to `auto`, `any` and named-tool choices only.
- Only `required` and named-tool choices count as forced for the thinking
  restriction; `auto` and `none` combine with thinking.

## Compatibility with recent tool work
Compaction keeps the client's `tools`, `tool_choice` and `parallel_tool_calls`
unchanged for cache preservation; this change does not touch that path.
Undeclared-tool validation, streamed-argument recovery, composed-schema
adaptation and OpenRouter tool-name bounding are independent of directive form.

## Reference
CLIProxyAPI PR #6341 (open on 2026-10-03), revision
`16a5d5f70aa46a72eb334e965b3e5c090bc89255`, reports the same object-form
`none` rejection in its Claude translation.
