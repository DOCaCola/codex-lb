# Verification (2026-10-01)

- Unit `test_claude_replay.py`, `test_claude_recovery.py`, `test_claude_protocol.py`,
  `test_claude_provider_history.py`, `test_compaction_compat.py`: all passed.
- Integration `test_source_compaction_completeness.py`: 38 passed (compact endpoints
  for available, paused owner, model switch, signature rejection, search and paused
  search; WebSocket trigger after a model switch). The model-switch case was run
  four times to confirm routing may select either account.
- Integration Haiku unsigned tool loop: disabled thinking on the loop request,
  budget thinking on the next user turn, request log modes `disabled`/`enabled`.
- Integration `-k "claude or compact"` serial: 816 passed, 86 skipped; one failure,
  `test_upstream_fork_heads_converge[20260929_010000_claude_routing]`, also fails on
  unmodified main.
- Unit `-k "claude or compact or replay or model_source"`: failures only in the
  known baseline modules (`test_model_source_request_headers`, `test_proxy_utils`,
  `test_db_migrate`, `test_codex_upstream_paths`, `test_proxy_security_work`);
  none in changed modules.
- `ruff check`, `ruff format --check`: clean. `ty check` on changed app modules:
  clean; changed test files have fewer diagnostics than before.
- `openspec validate claude-signed-history-portability` and `--specs` (75): valid.
- Not live-qualified: Anthropic acceptance of converted thinking text after a real
  model/account switch, Fable 5.1 prefix binding over projected history, and the
  disabled-thinking continuation on a production Haiku/Sonnet 4.5 account.
