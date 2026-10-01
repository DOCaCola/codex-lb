## Context and evidence
Codex d6c3b44 marks only `message` on `spawn_agent`, `send_message` and `followup_task` as encrypted (`multi_agents_spec.rs` `with_encrypted`). `ToolCall::direct_source` (`router.rs`) treats a `collaboration` call as plaintext only when `encrypted_function_args` is present and empty. Otherwise `InterAgentCommunication::to_model_input_item` sends the argument to the receiving agent as an `encrypted_content` part behind a plaintext header. The default namespace is `collaboration` (`config/mod.rs` `DEFAULT_MULTI_AGENT_V2_TOOL_NAMESPACE`), and no prompt text names it.

Live probes on 2026-10-01 through production codex-lb (gpt-6-luna, Codex's exact `send_message` schema):
- The reserved namespace with the marker returns ciphertext `gAAAA…`, without `encrypted_function_args`.
- The reserved namespace without the marker is rejected (`reserved for use by this model and must match the configured schema`).
- `collaboration-optimize` and `agent_collaboration` without the marker are accepted, and the model calls `send_message` with plaintext.
- History holding `collaboration` calls with plaintext arguments and `encrypted_function_args: []`, beside renamed tools, is accepted.
- A plaintext `agent_message` item is accepted.

References (inspected revisions):
- CLIProxyAPI d33f63f8 (`optimize-multi-agent-v2`, commits 1cf9a45c and 7fe84737): unconditionally strips `message.encrypted` from the three tools in `tools` and `input[].additional_tools`. It renames the `collaboration` namespace to `collaboration-optimize` and restores namespaces on responses (`RestoreCodexMultiAgentV2Response`). It lowers `agent_message` to user messages and turns `encrypted_content` parts into text (`normalizeCodexAgentMessages`). Because it omits `encrypted_function_args: []`, Codex still wraps the plaintext as `encrypted_content`.
- opencodex 8a005dd98 also lowers `agent_message` to a user turn. Real backend ciphertext is replaced with an omission marker on third-party routes.
- Sub2API 9a62841fd concatenates text and encrypted parts into one user message.
- OmniRoute 113de57b skips `agent_message` in its chat translator.

## Decisions
Make messages plaintext at the source. Lossy delivery would drop the report. A native rename is required, because upstream rejects the reserved namespace without the marker. The rename applies to every native request, whatever the destination: when an OpenAI child sends a message, codex-lb cannot know the recipient's provider. This matches CLIProxyAPI. OpenAI-to-OpenAI messages use Codex's own plaintext delivery path, which Codex already uses for non-OpenAI providers.

Reuse CLIProxyAPI's `collaboration-optimize` name, since it has the field record. The whole namespace moves, keeping the collaboration tools together. History calls keep their client namespace: the probe accepts them, and older OpenAI ciphertext in history keeps its reserved meaning.

Projection lives in `sanitize_native_responses_input`, the shared native boundary used by HTTP streaming, WebSocket `response.create`, the HTTP bridge and compact; every later frame rewrite starts from that text. Restoration happens at the two native readers: the `stream_responses` yield loop (HTTP SSE, its internal WebSocket and non-streaming JSON) and `ResponsesTransport._read_websocket`, the only reader of relay and bridge sockets. Request logs, replay, dedupe and continuity therefore see only `collaboration`. Restoration is stateless, so incremental WebSocket turns that omit tools are covered. Events are parsed only when their text contains the upstream name. Shared parsed payloads are copied, never mutated.

Translated providers lower `agent_message` once, in `_shape_source_responses_payload`: the shared boundary for Claude and model sources, after continuation expansion and before compaction requests reach the provider. The item becomes a user message. User messages have no sender fields, so its `author` and `recipient` are carried in Codex's own agent-message header (`Task name: …`, `Sender: …`, `Payload:`, from `InterAgentCommunication::to_model_input_item`), followed by the plaintext parts. Without it, a parent with several children could not tell who reported. An `encrypted_content` part can only be OpenAI ciphertext from before deployment; it raises `nonportable_agent_message` instead of being dropped or sent as unreadable text.

## Verification
Unit tests cover projection (tools, bundles and unrelated tools), restoration (items, completed output, echoed declarations, shared payload immutability) and both native readers. They also cover lowering of plaintext and encrypted `agent_message`, the Claude projection of a child report after a tool cycle, and model-source shaping. The #1184 WebSocket byte-identity regression now expects the collaboration projection and keeps every other byte unchanged. Followed by a live native probe through the projected schema and a production child-to-Claude-parent check after deployment.
