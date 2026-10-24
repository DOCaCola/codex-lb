# Design: Serve Messages Requests With Responses Models

## Reference comparison

Snapshots from 2026-10-23/24: agent-lb `81a8796`, CLIProxyAPI `8289ec4`, opencodex `9f0d40a25`, sub2api `37067e8e3`,
OmniRoute `5b3be70ba`.

| | agent-lb | CLIProxyAPI | opencodex | sub2api | OmniRoute |
|---|---|---|---|---|---|
| Architecture | Separate `/v1/ccgpt/messages`, one locked model | Direct translator (`translator/codex/claude`) | Translate, then replay through its Responses core | Direct translator plus a Chat fallback | Converts through Chat Completions |
| Model choice | Locked model; Claude names rejected | By name and aliases | Aliases, exact and date-less map | Per group: Opus/Sonnet/Haiku plus exact mappings | By name |
| Reasoning replay | `codex:` signature prefix, raw | Signature, provider-checked | `ocxr1` envelope, HMAC tag, same model only | Emits OpenAI blobs but drops them on input | Plain text only |
| Cache identity | none | Session + agent + model → `prompt_cache_key` and `Session-Id` | Hash of `metadata.user_id`, else model, system and tools cohort | Session, cache markers, then digest chain | none |
| Effort | `output_config.effort`, else high | Effort, or budget buckets | Effort, budget, disabled → none | Effort, max for Sol 6.1 | Effort and buckets |
| `count_tokens` | Local estimate | Local tiktoken | Local estimate | — | Provider count, else estimate |
| Overflow | 400 "prompt is too long" before output | — | Same phrase | — | — |
| Web search | Dropped | `web_search` with server tool blocks | — | `web_search` | Mapped |

CLIProxyAPI's history records the production failures this design must avoid:

| Commit | Fix |
|---|---|
| `8bc2eff5` | Tool call IDs over 64 characters |
| `d606faa9` | Claude Code attribution stripped from translations |
| `33f4904b` | Message-level system role → developer |
| `34639c3c` | Tool-call start deferred until the name is known |
| `94cf4674` | One thinking block per reasoning item |
| `baffbe2c` | Agent-scoped cache identity |
| `44d5e0be` | PDF documents preserved |
| `7fac6b15`, `e56abd56`, `aa365277` | Schema dialect keywords, Unicode property escapes, strict downgrade |
| `e365ab0c`, `883660fb` | Reasoning tokens reported as thinking tokens; cache writes deducted from input |
| `30dc2e7f`, `68afd0d1` | Web search server-tool blocks and sources |
| `376015c3` | Commentary phase rendered as thinking (2026-10-23) |

## Decisions

### 1. One dispatch, three ingress formats (opencodex)

The translated request is a `ResponsesRequest` handed to the dispatch that `v1_responses` uses after payload
parsing. That dispatch owns:

- account and source selection, stickiness and continuity
- API-key enforcement, reservations and fast-mode policy
- upstream WebSocket/HTTP bridging
- encrypted-content rejection recovery
- logging and pricing

Only the output projection differs. The Chat route already adds a projection (`chat_projection`); Messages adds a
third. This avoids a second upstream client, the main cost of agent-lb's separate route and of sub2api's parallel
gateway.

### 2. Routing by model name

API-key enforced models apply first, as in every other route. `anthropic/` and `claude-` names keep today's native
route, including the `anthropic/` prefixing. Anything else must resolve as an authorized Responses model. Server-side
family mapping (sub2api) is rejected: `claude-opus-*` must keep reaching real Claude accounts. Claude Code already
selects a model per family through its own settings.

### 3. Reasoning envelope (opencodex)

Signature format: `clb1:` + base64url(JSON `{"v":1,"model","enc","id","tag"}`). `tag` is an HMAC-SHA256 over model,
id and ciphertext, keyed with the installation key that `http_bridge_forwarding` already uses.

On replay, a valid envelope for the requested model becomes a reasoning item with `encrypted_content` and its
original id. Otherwise the block is dropped:

- envelopes for other models
- Claude signatures and other foreign signatures
- `redacted_thinking`

Summary-only reasoning items are not sent. With `store: false` they are looked up by id and fail; this is the
`rs_tmp` not-found failure seen in production. A malformed or forged `clb1:` envelope is rejected with 400.

Alternatives:

- agent-lb sends raw ciphertext. It breaks on model switches.
- sub2api never replays OpenAI blobs, which loses reasoning continuity and prefix cache. Its history gives no reason.
  The likely cause is ciphertext minted by another account. codex-lb already covers that: the cache identity keeps
  the conversation on its account, and rejected ciphertext digests are removed and retried.

The native Claude route removes `clb1:` thinking blocks before dispatch, as opencodex's `nativeAnthropicProjection`
does. A Claude Code session can therefore switch from GPT to Claude.

### 4. Commentary phase (CLIProxyAPI `376015c3`)

GPT commentary-phase messages become unsigned thinking blocks. `final_answer` and phaseless messages become text.
Unsigned thinking is not replayed, so commentary does not return to history, matching CLIProxyAPI.

### 5. Session and cache identity (CLIProxyAPI, opencodex fallback)

- Session: `x-claude-code-session-id` or the session in `metadata.user_id`, with today's disagreement check.
- Agent: `x-claude-code-agent-id`, defaulting to `main`.
- `prompt_cache_key`: a SHA-256 of model, session and agent. Account stickiness follows it through the existing
  prompt-cache affinity.
- Request logs record the Claude Code session as the conversation, like the other client conversation headers.
- Without a session, `prompt_cache_key` is opencodex's cohort hash: version, model, instructions and the translated
  tools in wire order.

Subagents therefore get their own cache lineage instead of evicting the parent's (the side-request issue).

### 5a. Fields without a Responses equivalent

Responses has no stop sequences and no `top_k`. Non-empty `stop_sequences`, `top_k`, `mcp_servers` and `container`
are rejected with `invalid_request_error` before dispatch instead of being silently ignored. Replayed
`server_tool_use` and `web_search_tool_result` blocks are omitted: the text that used them is already in the
assistant's text blocks, and Responses cannot replay hosted search without the original encrypted state.

Message-level system messages become developer messages. If tool calls are still pending at that point, the developer
message is placed after their outputs (CLIProxyAPI `9fdc4605`), because Responses requires each call to be followed
by its output.

### 6. Effort

| Input | Result |
|---|---|
| `output_config.effort` | Passes through |
| `thinking.type: enabled` with budget | CLIProxyAPI buckets: ≤512 minimal, ≤1024 low, ≤8192 medium, ≤24576 high, above that xhigh |
| `thinking.type: disabled` | `none` (opencodex #545) |
| Adaptive without effort | Unset, so the model default applies |

Existing per-model normalization and API-key effort policy then apply unchanged. Reasoning summaries are requested
unless thinking is disabled or its display is omitted.

### 7. Errors and compaction

`message_start` is held until the first upstream output event or terminal. A failure before that is an HTTP error with
an Anthropic envelope:

| Upstream | Downstream |
|---|---|
| `context_length_exceeded` | 400 `invalid_request_error`, "prompt is too long: …" |
| Quota or rate limit | 429 `rate_limit_error` with `retry-after` |
| Overload | 529 `overloaded_error` |
| Authentication or permission | 401 / 403 |
| Other 4xx | `invalid_request_error` |
| Other 5xx | `api_error` |

After output has started, failures are an in-band `error` event with no `message_stop`. Claude Code compacts
reactively only on the pre-output 400 (agent-lb spec).

### 8. Token counting

Translate, then estimate with the existing JSON token estimator. There is no new tokenizer dependency (agent-lb,
opencodex).

## Risks and checks

- **Context window:** Claude Code assumes a window for non-Claude names. If it is larger than a model's real window,
  reactive compaction carries the load. Verify in the mock harness.
- **Tool search:** Claude Code may send `defer_loading` tools or a tool-search server tool. Deferred tools are sent
  eagerly. Other server tools are rejected explicitly. Verify which tools Claude Code sends for non-Claude names.
- **Thinking/tool continuation on switch:** after a GPT→Claude switch, an open tool turn lacks a Claude-signed thinking
  block. Existing native behavior is unchanged and caller-owned; record the observed Anthropic response in the mock
  qualification.
- **Qualification:** OrbStack mock only (Claude Code → codex-lb → mock Responses upstream). No experiments against
  real servers.
