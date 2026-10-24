# Tasks

## 1. Aliases

- [x] 1.1 Encode and decode `clb-claude-` aliases in `app/core/messages/`.

## 2. Model list

- [x] 2.1 Serve the Anthropic models list from `/v1/models` for `anthropic-version` requests without
  `client_version`, with API-key visibility, Messages-servable models only, and OpenAI → Claude → other order.

## 3. Messages ingress

- [x] 3.1 Decode aliases before enforced-model and routing on `/v1/messages` and `/v1/messages/count_tokens`; echo the
  requested spelling in responses.

## 4. Verification

- [x] 4.1 Unit tests: alias round trip, escapes, invalid aliases.
- [x] 4.2 Integration tests: list shape and filtering, unchanged OpenAI and Codex lists, alias request logged under
  the decoded model.
- [x] 4.3 Lab: Claude Code 2.1.283 with discovery enabled lists and uses an aliased model.
- [x] 4.4 Full test suite, ruff, ty and `openspec validate --strict`.

## 5. Documentation

- [x] 5.1 `docs/client-setup.md`: enable discovery; `CLAUDE_CODE_MAX_CONTEXT_TOKENS` for routed models.
