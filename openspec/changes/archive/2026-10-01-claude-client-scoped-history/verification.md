# Verification (2026-10-01)

- All Claude and native-history unit/integration files, serial: 1024 passed.
- New coverage: translated fork replay with completed (preferred owner) and active (strict owner) parent thinking; native Messages fork replaying a server resource on its origin; foreign-client and tampered envelopes still fail before account selection.
- Parallel (`-n 8`) runs of `test_claude_inference.py`/`test_claude_provider_history.py` fail intermittently on the unchanged baseline as well (12 failures); not caused by this change.
- `ruff check`, `ruff format --check`: passed. `ty check app`: 6 diagnostics, all in untouched files (pre-existing).
- `openspec validate` (change strict, 75 specs): passed. `uv lock --check`: passed.
- Production had zero `claude_resource_origins` rows, so rekeying needs no migration.
- No live Anthropic inference. Upstream acceptance of parent signatures under a new session ID rests on native Claude Code fork behavior, not on mocks.
