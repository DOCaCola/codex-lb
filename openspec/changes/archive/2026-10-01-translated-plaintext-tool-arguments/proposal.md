## Why
On 2026-10-01 an Opus parent spawned a GPT-6.1 Sol subagent, and every child request failed with `invalid_encrypted_content` (12 retries, conversation 01a0f8a8, 18:10–18:17Z). Codex flags the `message` parameter of its collaboration tools as `encrypted`. The OpenAI backend encrypts those arguments and states on each `function_call` which ones it encrypted (`encrypted_function_args`). Calls that codex-lb translates from Claude or forwards from model sources carry plaintext but omit that field. Codex therefore treats the plaintext task as ciphertext and hands it to the child as an `encrypted_content` part, which OpenAI cannot decrypt.

## What Changes
Function calls produced outside the OpenAI backend for tools that declare encrypted parameters SHALL state `encrypted_function_args: []` on every public Responses item: streamed added/done items and final output. Both the translated Claude path and model-source Responses forwarding apply this, based on the client's own tool declarations.

## Capabilities
### New Capabilities
### Modified Capabilities
- `claude-accounts`: translated tool calls declare plaintext arguments.
- `model-source-routing`: forwarded source tool calls declare plaintext arguments.

## Impact
Claude Responses projection, model-source Responses forwarding (HTTP and stream), shared declaration helper and tests. No migration, settings or native Messages change. Conversations whose history already holds a misdelivered task stay unusable on OpenAI models and must respawn the child. The reverse direction, where OpenAI ciphertext reaches a Claude or source child, is out of scope.
