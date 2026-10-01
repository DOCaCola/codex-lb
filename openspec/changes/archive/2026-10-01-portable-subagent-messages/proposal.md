## Why
On 2026-10-01 at 18:43:45Z a GPT-6.1 Sol child sent its first progress message to its Claude Opus parent. The parent's next request failed with `Unsupported Claude Responses item: agent_message` (request cf032b98). Codex delivers inter-agent messages as `agent_message` items, and the Claude adapter rejects that type. The message also carried the child's text as OpenAI backend ciphertext (`gAAAA…`), which no other provider can read. Teaching the adapter the item type alone would therefore still lose the report.

The ciphertext comes from the reserved OpenAI `collaboration` namespace. Its `spawn_agent`, `send_message` and `followup_task` tools mark `message` as `encrypted`, and the backend requires that exact schema: removing the marker returns `Function 'collaboration.send_message' is reserved for use by this model and must match the configured schema` (live probe, gpt-6-luna). codex-lb serves one agent tree across OpenAI, Claude and model sources, so inter-agent messages must stay readable for every provider.

## What Changes
- Native ChatGPT Responses requests SHALL declare a client `collaboration` namespace upstream as `collaboration-optimize`, with the `encrypted` parameter markers removed, in `tools` and `additional_tools` input bundles.
- Native output SHALL restore function calls and echoed namespace declarations to `collaboration` before any other processing. Restored calls SHALL carry `encrypted_function_args: []`, so Codex delivers the message as plaintext.
- Claude and model-source Responses requests SHALL accept plaintext `agent_message` items as user turns. An `agent_message` whose content still contains `encrypted_content` SHALL fail explicitly with `nonportable_agent_message`.

## Capabilities
### New Capabilities
### Modified Capabilities
- `responses-api-compat`: plaintext collaboration tools on the native boundary.
- `claude-accounts`: inter-agent messages are user turns.
- `model-source-routing`: inter-agent messages are user messages.

## Impact
Native request sanitation, `stream_responses` and the Responses WebSocket transport read path, the Claude Responses projection, model-source Responses forwarding, and tests. No migration or settings. Native prompt caches miss once, because the tool prefix changes. Messages exchanged before deployment stay ciphertext in client history: OpenAI parents still read them, and Claude or source parents reject them explicitly, so the child must be respawned.
