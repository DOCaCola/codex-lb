## Why
Codex selects its multi-agent protocol from the catalog entry of a tree's root model. Claude catalog entries omit `multi_agent_version`, so Claude-rooted trees run v1: children get no `send_message`, and a report from a child turn the parent did not start never reaches the parent. In v2, reports travel as plaintext `agent_message` items that codex-lb already makes portable across OpenAI, Claude and model sources.

Lowered agent messages also carry the inter-agent header twice: codex-lb prepends `Task name/Sender/Payload`, but Codex already renders its full header (`Message Type`, `Task name`, `Sender`, `Payload`) inside the content.

v2 forks copy the parent's history into children by default (`fork_turns: "all"`), so mixed-provider trees replay one provider's history on another. Today three cases reject the child's first request:

- Claude redacted thinking sent to OpenAI fails with `nonportable_provider_history`.
- Claude hosted search sent to OpenAI fails with `nonportable_provider_history`.
- OpenAI's own `web_search_call` history sent to Claude fails with "Claude search history requires its account-bound opaque state".

A Claude hosted search also blocks a switch to another Claude model or account even after the turn is complete, for example an Opus parent forking a Sonnet child. The same failures hit an ordinary user model switch. CLIProxyAPI, opencodex and Sub2API translate instead: they drop private state and keep only the readable search query and sources.

## What Changes
- Claude catalog models advertise `multi_agent_version: "v2"`.
- Lowering an `agent_message` to a user message forwards its content unchanged, without an added header.
- History sent to another provider omits Claude redacted thinking and counts the omission. Encrypted reasoning from OpenAI is already handled this way.
- Hosted searches sent to another provider become readable assistant text: the query, page or pattern, plus result titles and URLs. This covers both completed and active turns, matching foreign reasoning. Completed Claude searches sent to another Claude model or account are projected the same way. Encrypted search results go only to their original Claude owner and model, as before, and an active-turn search between Claude routes stays bound to that owner and model.
- A lab case validates `fork_turns: "all"` in both directions, with redacted thinking and search in the parent's history.

## Capabilities
### Modified Capabilities
- `claude-accounts`: catalog multi-agent version; agent-message lowering; cross-route projection of redacted thinking and hosted search.
- `model-source-routing`: agent-message lowering.

## Impact
Catalog projection (`app/modules/model_sources/catalog.py`), `app/core/openai/subagent_messages.py`, and Claude history projection (`app/modules/claude/replay.py`, `app/modules/claude/protocol.py`). No schema, setting or deployment configuration change. Retained history is unchanged; only outbound projection differs. The catalog change applies to agent trees created after clients refresh the catalog, and existing trees keep their persisted version. The history projection applies to every request, including model switches outside agent trees.
