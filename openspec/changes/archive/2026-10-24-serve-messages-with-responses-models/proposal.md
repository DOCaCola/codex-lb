# Serve Messages Requests With Responses Models

## Why

Claude Code speaks only the Anthropic Messages API. `/v1/messages` prefixes every model name with `anthropic/` and
sends it through Claude dispatch, so Claude Code cannot use OpenAI/Codex accounts or OpenRouter models: a request for
`gpt-6.1-sol` becomes `anthropic/gpt-6.1-sol` and is rejected before dispatch.

All five references serve Claude Code from OpenAI/Responses models: agent-lb, CLIProxyAPI, opencodex, sub2api and
OmniRoute. They agree on most of the wire mapping. They differ mainly in architecture, reasoning continuity and session
identity; `design.md` compares them.

## What Changes

- `/v1/messages` and `/v1/messages/count_tokens` route by model. `anthropic/` and `claude-` names keep the native
  Claude path. Any other name resolves as a Responses model (native catalog or enabled model source) and is served by
  translation.
- Translated requests become one `ResponsesRequest` that runs through the existing `/v1/responses` dispatch.
  Account selection, stickiness, model sources, API-key limits, fast-mode policy, encrypted-content recovery, logging
  and pricing therefore stay in one place (opencodex architecture).
- Request and stream conversion follows CLIProxyAPI's Codex⇄Claude translator, including its production fixes:
  - tool name and call ID aliasing beyond 64 characters
  - schema cleanup
  - Claude Code billing attribution removed
  - commentary phase shown as thinking
  - one thinking block per reasoning item
  - deferred tool-call start
  - cache-adjusted input usage and reasoning token reporting
  - PDF documents
  - hosted web search
- Encrypted reasoning returns to Claude Code inside a signed, versioned thinking-signature envelope bound to the
  client-facing model. It replays only to that model (opencodex). The native Claude path removes these envelopes
  before dispatch.
- Upstream context overflow before any output becomes HTTP 400 `invalid_request_error` "prompt is too long", so
  Claude Code compacts reactively (agent-lb, opencodex). Other errors become Anthropic error envelopes.
- `count_tokens` for translated models is a local estimate. It selects no account and sends nothing upstream.
- Prompt-cache and conversation identity derive from the Claude Code session and agent IDs (CLIProxyAPI). Without
  them, identity derives from a model, instructions and tools cohort (opencodex).

## Non-goals

- Server-side mapping of Claude names to GPT models. Claude Code's own model settings choose the model per family
  (`ANTHROPIC_DEFAULT_OPUS_MODEL`, `_SONNET_`, `_HAIKU_`).
- Emulating Anthropic `context_management` edits, tool search or other server tools apart from web search.
- Model sources that support only Chat Completions.
- Changes to translated Responses or Chat requests served by Claude.

## Capabilities

### New Capabilities

- `messages-api-compat`: Anthropic Messages ingress served by Responses models.

### Modified Capabilities

- `claude-accounts`: "Native Messages fidelity" is limited to Claude models and removes proxy reasoning envelopes.

## Impact

- `app/modules/proxy/api.py`: `claude_messages` routing; translated dispatch shared with `v1_responses`.
- New `app/core/messages/` translator: request mapping, stream and non-stream projection, reasoning envelope,
  error mapping, token estimate.
- `app/modules/claude/dispatch.py` / `wire_identity.py`: envelope stripping and session/agent identity reuse.
- Request logging of the Messages ingress; tests; user docs for Claude Code configuration.
