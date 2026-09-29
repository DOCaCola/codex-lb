## Why
The deployed Claude adapter rejects Codex external task envelopes with omitted or null `call_id` before upstream dispatch. Codex history uses optional call identifiers for these user inputs, unlike real tool results. OpenCodex issue #3807 and its merged fix provide matching source and regression evidence.

## What Changes
Recognize complete external task inputs using one shared classifier for protocol projection and replay user-turn boundaries. Preserve supported text/images as user input without inventing a tool cycle or changing logical history. Reject incomplete envelopes, wrong-typed identifiers and interrupted tool cycles. Extend content-free rejection diagnostics and test public HTTP/WebSocket and retained continuation paths.

## Capabilities
### Modified Capabilities
- `claude-accounts`: canonical Codex external task input and replay boundaries.

## Impact
Translated Claude Responses only; native Messages, storage lifetime, authentication and server-resource ownership remain unchanged. No migration, configuration, commit or deployment is required by this implementation task.
