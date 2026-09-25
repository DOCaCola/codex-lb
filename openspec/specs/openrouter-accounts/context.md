# Implementation context

OpenRouter accounts reuse model-source scoping, encrypted inference credentials and accounting rather than masquerading as subscription accounts. An extension table stores the synchronized provider snapshot, operator selections and optional management credential. Optimistic version checks prevent a slow refresh from overwriting an operator's concurrent selection edit.

The client WebSocket bridge follows OpenCodex's separation of downstream transport from provider transport: it calls the existing Responses route in-process, streams SSE events as WebSocket frames, and closes owned work on disconnect. It does not imitate OmniRoute's proprietary `/v1/ws` protocol or require OpenRouter to accept upstream WebSockets.

OpenRouter's Responses API rejects stored continuation. Existing private replay storage materializes complete history, using client-key and conversation identity. Unknown handles produce an explicit full-resend request. No account substitution occurs after response delivery begins. Provider 403 responses are not retried across credentials; the gateway does not attempt to bypass access or moderation restrictions.

For example, selecting `z-ai/glm-5.3-flash` publishes `openrouter/z-ai/glm-5.3-flash` with a default 262144-token cap. The upstream receives `z-ai/glm-5.3-flash`, price-first provider selection and `store:false` over HTTPS while Codex receives events on its existing WebSocket.

Operator setup and monitoring details: [native OpenRouter accounts](../../../docs/openrouter-accounts.md).
