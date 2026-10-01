# Verification — 2026-10-01

Implemented Claude cache-preserving compaction. Not committed, pushed or deployed.

- 161 focused tests passed: compaction compat/markers, Claude replay and
  provider history, all source compaction completeness integration tests and the
  OpenRouter selected-provider compaction test.
- New coverage: Claude compact endpoint and WebSocket trigger reuse the turn's
  tools, tool choice, system and message prefix; a tool_use summary returns
  model_source_compaction_invalid with retained history unchanged; OpenRouter
  summarization stays tool-free when tools are declared; native terminal compact
  requests carry no tool fields.
- Serial integration run (`-k "claude or compact or handoff or openrouter"`):
  949 passed. The 3 failures (two HTTP bridge handoff tests and
  `test_upstream_fork_heads_converge[20260929_010000_claude_routing]`) and the
  unit failure `test_compact_responses_sanitizes_foreign_reasoning_for_native_upstream`
  also fail on unmodified HEAD f0f0212b3. Parallel (`-n auto`) runs of the
  completeness tests interfere with each other; they pass serially.
- Ruff lint and format passed for changed files; ty passed for changed modules.
- Strict validation passed for this change and all 75 main specs; `git diff --check` passed.

Pending: live confirmation of cache reads on the next Claude compaction.
