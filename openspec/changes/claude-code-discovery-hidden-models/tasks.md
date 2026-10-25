# Tasks

## 1. Model list

- [x] 1.1 Omit models whose catalog visibility is not `list` from the Anthropic models list.

## 2. Verification

- [x] 2.1 Integration test: `codex-auto-review` is absent from the Anthropic list and present in the OpenAI list.
- [x] 2.2 Full test suite, ruff, ty and `openspec validate --strict`.
