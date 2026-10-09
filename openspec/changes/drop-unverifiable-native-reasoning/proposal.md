# Drop Unverifiable Native Reasoning

## Why

Native dispatch turns readable Claude thinking, and plaintext reasoning from other model sources, into summary-only
`reasoning` items. OpenAI accepts such items as fresh input and stores them with the response. When the next turn
chains onto that response with `previous_response_id`, OpenAI rejects it with `unsupported_persisted_item_context`:
the stored response contains "unverifiable hidden reasoning state". This happened in production after a thread
switched from Claude Opus 5.5 to gpt-6-astra: the first astra turn succeeded, and the next chained turn failed.

The references agree that a reasoning item may reach an OpenAI target only as that provider's own opaque state.
CLIProxyAPI replays Claude thinking only when its signature is a genuine Codex reasoning blob and otherwise drops it,
never replaying the text. sub2api replays thinking only as provider ciphertext and ignores unsigned thinking. OmniRoute
treats Codex/Responses targets as opaque-only: plaintext reasoning is removed, and summary-only leftovers are removed
when `store=false`.

## What Changes

- Native Codex dispatch omits authenticated Claude thinking, as it already omits redacted thinking. Authentication,
  hosted-search projection and retained history are unchanged.
- The native boundary forwards a `reasoning` item only when it carries non-empty `encrypted_content`. Native requests
  are always `store=false`, so a reasoning item without it is never a lookup reference. Plaintext `content` on a kept
  item is cleared rather than moved into its summary.
- Diagnostics count omitted items without content.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: "Claude history at native Codex dispatch" omits Claude thinking and unverifiable reasoning.

## Impact

- `app/modules/claude/replay.py` `project_native_replay` and `app/core/openai/reasoning.py`
  `sanitize_native_reasoning_input`. HTTP, WebSocket, retained continuation and native compaction share both.
- Switching to a native model loses the other provider's private reasoning text; visible messages, tool calls and
  tool results are unchanged. Switching back replays the retained originals.
- Model-source (OpenRouter) dispatch and Claude dispatch are unchanged.
