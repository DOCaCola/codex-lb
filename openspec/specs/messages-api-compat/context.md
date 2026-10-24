# Messages API Compatibility Context

## Purpose and Scope

`/v1/messages` serves Claude Code and other Anthropic Messages clients. Claude model names (`claude-*`,
`anthropic/*`) use the native Claude route described in `claude-accounts`. Any other name is translated to one
Responses request and served by OpenAI accounts or a Responses-capable model source such as OpenRouter.

See `openspec/specs/messages-api-compat/spec.md` for normative requirements.

## Architecture

The translated request is dispatched by `_serve_v1_responses`, the same function that serves `/v1/responses` after
ingress parsing. Account and source selection, prompt-cache stickiness, API-key limits, fast-mode policy,
encrypted-content recovery, request logging and pricing therefore behave as on `/v1/responses`. Only the response
projection differs (`app/modules/proxy/messages_projection.py`). This follows opencodex; agent-lb and sub2api run a
separate upstream client for this ingress.

- `app/core/messages/translate.py`: Messages request to Responses (CLIProxyAPI's Codex/Claude translator).
- `app/core/messages/stream.py`: Responses events to Messages events, and non-streaming aggregation.
- `app/core/messages/envelope.py`: signed reasoning envelope and its removal on the native route.
- `app/core/messages/errors.py`: Anthropic error envelopes.
- `app/core/messages/tokens.py`: local `count_tokens` estimate.

## Decisions

- **Reasoning envelope.** Encrypted reasoning travels in the thinking signature as `clb1:` plus base64url JSON with
  the client-facing model, the reasoning item ID, the ciphertext and an HMAC tag. The key is derived from the
  installation encryption key. Replay is limited to the same model; other envelopes, Claude signatures, unsigned and
  redacted thinking are left out. A forged or malformed `clb1:` signature is rejected, because it can only come
  from tampering. The native route removes `clb1:` thinking so a session can switch from GPT to Claude.
- **Summary-only reasoning items are never sent.** With `store: false` they are resolved by ID upstream and fail
  (the `rs_tmp` not-found error seen in production). A reasoning item without encrypted content becomes an
  unsigned thinking block and is not replayed.
- **Identity.** `prompt_cache_key` hashes model, Claude Code session and agent, so stickiness follows the session and
  subagents keep separate cache lineages (CLIProxyAPI `baffbe2c`). Without a session, the key hashes model,
  instructions and tools (opencodex cohort). The request-log conversation is the Claude Code session header.
- **Held start.** `message_start` waits for the first output or terminal event, up to 10 seconds. A failure before
  that becomes an HTTP error; context overflow becomes 400 "prompt is too long", which triggers Claude Code's
  reactive compaction (agent-lb, opencodex). After output, failures are an in-band `error` event without
  `message_stop`. The dispatch stream is always consumed to its end, so settlement and logging complete.
- **Rejected fields.** Responses has no stop sequences or `top_k`; MCP connectors and containers have no
  equivalent. They are rejected instead of being dropped silently.
- **Commentary.** GPT commentary-phase messages become unsigned thinking blocks (CLIProxyAPI `376015c3`), so
  clients show the answer once.
- **Usage.** `input_tokens` excludes cache reads and writes, which are reported separately; output tokens include
  reasoning (CLIProxyAPI `883660fb`).

## Constraints

- Anthropic Files API references (`source.type: file`) are rejected; they are not portable to Responses.
- `count_tokens` is a characters/4 estimate with bounded per-attachment costs; it selects no account.
- Replayed web-search blocks are omitted; the answer text already carries their content.
