# Verification (2026-09-29)

- Claude unit/integration suite: 561 passed before the final two regressions.
- Final focused schema suites: 46 passed, including those two additions.
- `make lint`: passed (existing repaired migration timestamp warning only).
- `uv run ty check app/modules/claude`: passed.
- `uv lock --check`: passed.
- Strict change validation and all 73 main specifications: passed.
- HTTP and WebSocket public routes verify fragmented arguments, namespaced calls,
  durable continuation and transport cleanup. Malformed wrapped arguments never
  publish argument deltas/done or successful completion.
- Native Messages schema preservation and complete-message decoding are covered.
- No live Anthropic inference was used for these tests. Exact envelope acceptance
  remains a production qualification step, not a conclusion from mocks.
- Claude Chat Completions routing was found to be absent and remains outside this
  fix; no support claim or synthetic passing test is made for that route.
