# Design: Claude Code Model Discovery

## Claude Code behaviour (2.1.283 binary)

- Discovery runs only with `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY`, a non-first-party `ANTHROPIC_BASE_URL` and a
  credential. It sends `GET <base>/v1/models?limit=1000` with `anthropic-version: 2023-06-01`, `Authorization` and/or
  `x-api-key`.
- The body must validate as `{data: [{id, display_name?, description?}]}`; other fields are stripped. Entries whose ID
  does not match `/(claude|anthropic)/i` are discarded. The result is cached in
  `~/.claude/cache/gateway-models.json` against the base URL.
- For an unrecognised model Claude Code assumes a default context window. It honours
  `CLAUDE_CODE_MAX_CONTEXT_TOKENS` only for IDs it does not treat as its own; an unknown `claude-` ID is treated as an
  Anthropic model (opencodex `src/claude/alias.ts`, confirmed in the binary).

## Reference: opencodex (`9f0d40a25`)

- Detection: `anthropic-version` header or `?flavor=anthropic`, without `client_version`
  (`src/server/index/serve-options.ts`).
- Routed models: `ocx-claude-<provider>--<model>`; slashes and tildes escaped under `ocx-claude2-` (`~s`, `~t`). The
  first spelling, `claude-ocx-`, was replaced because of the `claude-` context behaviour above; old prefixes still
  decode. Real Anthropic models keep their ID.
- Display names state the real model (`gpt-… (native)`); descriptions say how it is routed.
- The Messages ingress resolves the alias and echoes the requested spelling in responses.

## Decisions

### Alias format

`clb-claude-<model>`, with `~` encoded as `~t` and `/` as `~s` (in that order). codex-lb model names are already unique
across accounts and sources, so opencodex's provider segment is unnecessary and every name is representable. The ID
contains `claude` but does not start with `claude-`. Decoding expands `~s` and `~t`; any other `~` sequence makes
the alias invalid. Example: `openrouter/z-ai/glm-5.3-flash` → `clb-claude-openrouter~sz-ai~sglm-5.3-flash`.

### List contents

Only models `/v1/messages` can serve: native OpenAI models, Claude models, and source models whose source supports
Responses. Chat-only source models are omitted. API-key visibility follows the existing `/v1/models` rules. Claude
models are listed by their Anthropic ID, without `anthropic/`.

Entries use the Anthropic `ModelInfo` shape: `type: "model"`, `id`, `display_name`, `created_at`, plus
`description`, `max_input_tokens` and `max_tokens` when known. `has_more` is `false`; `first_id` and `last_id` name the
ends of the list. `limit` and cursors are not applied: the list is small and Claude Code requests 1000.

### Request handling

The alias is decoded before the enforced-model rule, so a key's enforced model still wins. The envelope for
reasoning replay binds the decoded model, so selecting the same model by alias or by name continues one reasoning
chain. The projected response reports the requested spelling, as opencodex does, so Claude Code's own model
bookkeeping matches its selection.

### Context windows

No `[1m]` rows. The docs explain `CLAUDE_CODE_MAX_CONTEXT_TOKENS`. Overflow already returns "prompt is too long",
so a larger window than the model supports is recovered by compaction.
