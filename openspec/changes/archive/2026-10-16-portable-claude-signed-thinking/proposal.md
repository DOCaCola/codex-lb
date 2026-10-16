# Portable Claude Signed Thinking

## Why

On 16 Oct 12:32:46 UTC, request `ws_src_1de61b35f43948dc9b10f0ceeddacf59` (conversation
`01a0e444-cbc2-77f0-9741-8d15819ba5f3`) failed locally with 400 "Invalid request payload". The user had stopped an
Opus 5.5 tool loop, switched to Sonnet 5.5 and resumed without typing. Codex sends the interrupt marker as a developer
message, so no user turn followed the Opus thinking. `authenticate_replay` treated that thinking as active and rejected
the model switch ("Active Claude reasoning or search requires its original model"). The error had no code, so the
generic payload error replaced its message.

Anthropic now documents the opposite contract (preserved thinking, read 2026-10-16): keep sending every thinking block
unchanged across model and account switches. The API drops blocks the target cannot read (`model_binding_mismatch`,
`organization_binding_mismatch`) without error or billing. Only edits to the prefix before a block are rejected. Our
omission policy also violated that rule: switching back to a model re-inserted thinking it had omitted earlier, which
Anthropic lists as invalid for every later block. CLIProxyAPI and OmniRoute forward Claude thinking to any Claude target;
none of the references rejects a Claude-to-Claude switch.

## What Changes

- Authenticated signed and redacted thinking is forwarded verbatim to any Claude account and model, in completed and
  active turns. Its producer is only a routing preference.
- Active hosted search keeps its strict account/model binding; completed search keeps its portable text projection.
- Compaction still converts completed thinking produced on another route into readable text, so the summary keeps
  content Anthropic would drop; active thinking is forwarded verbatim.
- Signed-history errors carry `invalid_provider_history` or `nonportable_provider_history` and their input index,
  so clients see the specific message. The model-checking `ClaudeOpaqueState.decode` is removed.
- The existing one-shot signature recovery stays unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: "Translated completed reasoning recovery", "External task replay boundary" and "Foreign reasoning
  at Claude dispatch" drop account/model ownership of thinking.
- `model-source-routing`: "Source compaction history safety" forwards active thinking on any Claude route.

## Impact

- `app/modules/claude/replay.py`, `app/modules/claude/opaque.py`, `app/modules/claude/inference.py`,
  `app/modules/claude/chat_replay.py` (error codes).
- Unit and integration tests for replay, provider history, protocol, search and translated inference.
