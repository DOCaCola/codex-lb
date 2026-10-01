## Context and evidence
Codex d6c3b44: `ToolCall::direct_source` (core/src/tools/router.rs) yields plaintext delivery only for `collaboration` `spawn_agent`/`send_message`/`followup_task` calls whose `encrypted_function_args` is present and empty; otherwise `agent_message_from_tool` treats the argument as ciphertext and `InterAgentCommunication::to_model_input_item` emits an `encrypted_content` part. Parameters are marked through the schema's `encrypted: true` (multi_agents_spec.rs `with_encrypted`).

References inspected 2026-10-01: OmniRoute 113de57b fixed the same failure (#14154, commit 38cbb7ef) by stamping `encrypted_function_args: []` on translated collaboration calls. CLIProxyAPI d33f63f8 instead rewrites `agent_message` encrypted parts into text on requests to non-Codex models, which repairs the symptom on one destination but leaves the client's history mislabelled.

## Decisions
Follow OmniRoute's source-side correction, but derive scope from the request's tool declarations (any function whose top-level parameter properties carry `encrypted: true`) rather than hard-coded names. The marker is a factual statement that the provider encrypted nothing, applies only where the client asked for encryption, and stays correct if Codex adds encrypted parameters elsewhere. The declaration set is computed from the client payload before provider-specific name projection so namespace identity is preserved. Claude records the fact on its tool identity; model sources record it on the request-local `ToolNames` state, which already rewrites every public output item and stream frame.

History items carrying the marker need no inbound handling: Claude projection reads only named fields, and model sources receive the field as the client sent it.

## Verification
Unit coverage of declaration detection, Claude streamed/non-stream function calls with and without encrypted parameters, and source HTTP/stream restoration with and without OpenRouter name projection. Production evidence from request logs; no live provider calls.
