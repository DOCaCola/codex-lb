## Decision
Follow Claude Code's `/compact` fork (cache-safe parameters: same system, tools
and messages; tool use denied; trailing plain-text reminder) and Codex CLI's
remote compaction v2, which sends model-visible tools and
`parallel_tool_calls: true` like normal turns. OpenCodex's tool-free summary,
the origin of the previous behavior, does not account for Claude's
tools -> system -> messages cache order.

`build_terminal_compact_request` carries tool declarations only for the source
path; the native compact request keeps its existing fields.
`build_source_compaction_request` copies them into the summarization turn only
for Claude sources. Codex never sends `additional_tools` bundles to sources
(source catalogs advertise responses-lite off), and Claude turns reject them, so
removing them from compaction input changes no Claude prefix.

The reminder is a second text part of the single summarization instruction for
every source. It sits after the cached history, and it is harmless for tool-free
sources. The completed-summary extractor accepts only message and reasoning
output, so a tool, custom-tool or hosted-search call fails with
model_source_compaction_invalid. Checkpoint handoff shares the extractor and
already rejected other output types, so its duplicate check is removed.

`tool_choice: none` is not used: Anthropic invalidates cached messages when tool
choice changes. A forced client tool choice is forwarded unchanged; forcing a
tool during compaction fails through output rejection.

## Expected effect
With the previous turn's breakpoints reused, the 161,933-token compaction bills
mostly as cache reads (Opus: $0.50/M vs $6.25/M writes). Roughly $0.25 instead
of $0.94, most of it the summary's 6.5k output tokens. This needs confirmation
on the next live compaction (`request_logs.cached_input_tokens > 0` with
`request_operation='compaction'`).
