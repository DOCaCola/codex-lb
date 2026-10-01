# Verification (2026-10-01)

- Unit `test_claude_provider_history.py`, `test_claude_replay.py`, `test_compaction_compat.py`: 79 passed.
- Integration `test_source_compaction_completeness.py`: 34 passed. With the previous
  replay code, 8 of the 10 new switch/open-loop cases fail.
- Integration `-k "claude or compact"` serial: 811 passed, 86 skipped; one failure,
  `test_upstream_fork_heads_converge[20260929_010000_claude_routing]`, also fails on
  unmodified `b195141d5`.
- Unit `-k "claude or compact or replay or model_source"`: the same 45 failures with
  and without this change (stale fixtures, e.g. `SimpleNamespace` sources without
  `kind`); none touch the changed modules.
- `ruff check`, `ruff format --check`, `ty check` on changed files: clean. The
  proxy architecture line-count check fails identically on unmodified `b195141d5`.
- `openspec validate claude-compaction-turn-boundary` and `--specs` (75): valid.
- Not live-qualified: Claude acceptance of the summarizer request after a real
  Sol-to-Opus switch in production.
