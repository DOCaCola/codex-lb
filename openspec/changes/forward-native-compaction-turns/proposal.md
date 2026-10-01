## Why
HTTP Codex compaction turns (`/backend-api/codex/responses` with a terminal
`compaction_trigger`) on subscription accounts are rebuilt as compact requests:
tools, `tool_choice`, text options and client metadata are removed,
`parallel_tool_calls` is forced off and the input is trimmed to ~100k estimated
tokens. The changed prefix misses the prompt cache (0 cached on every observed
HTTP compaction, 200k+ tokens each) and the summarizer sees only 20–35% of the
history. The rebuild dates from #977, when upstream `/responses` did not answer
the trigger; since #1809 the compact leg itself already uses `/responses`, and
websocket and frame-size HTTP turns forward the trigger unchanged with ~0.99
cache ratio. The minted HTTP turn state of the compact branch is also never
bound to an owner, so the next turn may move account.

Reference behaviour (2026-10-01): the Codex CLI sends the trigger turn with its
tools and `parallel_tool_calls: true`; sub2api, opencodex, CLIProxyAPI and
OmniRoute forward native trigger turns unchanged and only rewrite them for
providers without native compaction.

## What Changes
- Subscription-served HTTP trigger turns use the ordinary bridge/streaming path.
- The HTTP bridge and direct streaming path record native checkpoint provenance
  for completed compaction turns, as the websocket path does.
- Explicit `/responses/compact` callers and source compaction keep their
  compact handling; source compaction always keeps tool declarations.

## Capabilities
### Modified Capabilities
- `responses-api-compat`: Codex HTTP compaction triggers are forwarded turns.

## Impact
Native HTTP compaction only. No migration or client change.
