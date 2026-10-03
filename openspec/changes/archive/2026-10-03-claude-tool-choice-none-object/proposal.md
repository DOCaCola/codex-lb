## Why
Responses and Chat clients may send the tool-choice directive in object form,
such as `{"type": "none"}`. The Claude projection treated it as a named-tool
choice and rejected the request with "Unknown tool choice". It would also have
refused the object form alongside thinking as a forced choice.

## What Changes
Collapse object-form `auto`, `none` and `required` directives to their string
form inside the Claude projection, before named-tool lookup. Keep tool
declarations and history. Send `disable_parallel_tool_use` only for choices
that can call tools. Directive objects with extra fields fail explicitly.

## Impact
Claude projection for `/v1/responses`, `/v1/chat/completions` and the Codex
route. Shared OpenAI request normalization, native passthrough, compaction and
OpenRouter tool naming are unchanged. Codex sends string `auto` and is
unaffected.
