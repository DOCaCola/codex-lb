# OpenRouter Message Phase

## Why

OpenRouter's Responses API relays the assistant message `phase` only from models that emit it natively (OpenAI's
GPT-5.3 Codex through GPT-5.5 Pro); every other model's messages arrive with `phase: null`. codex-lb relays OpenRouter
output unchanged, so answers from GLM, Qwen, MiniMax and similar models reach Codex without a phase:

- Forked threads keep only assistant messages whose phase is `final_answer` (`keep_forked_rollout_item`), so a child
  forked from an OpenRouter parent loses every answer the parent gave.
- A `commentary` message marks work still in progress, which allows mailbox preemption between tool calls.

opencodex infers the phase for every translated provider when it closes a message (`src/bridge/sse.ts`
`closeCurrentMessage`): commentary when more output follows, final answer at a clean finish, none when truncated, and
an upstream phase always wins. Translated Claude responses already follow the same rule (`claude-message-phase`).

## What Changes

- An assistant message without a phase is delivered with `commentary` when another output item follows it.
- The last such message of a completed response is `final_answer`, or `commentary` when the response requests a
  client tool call; an incomplete or failed response leaves it without a phase.
- A phase sent by OpenRouter is kept unchanged.
- The streamed `output_item.done` is held until the phase is known; the terminal response output carries the same
  phases, so replayed history keeps them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `openrouter-accounts`: adds "OpenRouter assistant messages carry a Responses phase".

## Impact

- New `app/modules/openrouter/phase.py`; `app/modules/model_sources/forwarding.py` applies it to streamed and
  non-streamed OpenRouter Responses; `app/modules/openrouter/tool_names.py` shares its SSE framing.
- Generic OpenAI-compatible sources and native passthrough are unchanged.
