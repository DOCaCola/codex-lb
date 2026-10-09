# Verification — 2026-09-30

Implemented client metadata policy only. Provider capabilities, output ceilings
and explicit shared context overrides remain intact. No compaction-history
implementation, production changes, commit or deployment are included.

- 143 tests passed across `test_model_sources_catalog.py`,
  `test_claude_catalog.py`, `test_claude_accounts.py`, and `test_v1_models.py`.
- Coverage includes existing/stale projections, 1M/750k/200k/64k capacity,
  unrelated provider isolation, output preservation, persisted capacity,
  both public model-list endpoints and explicit context overrides.
- Ruff lint and format checks passed for all seven changed context-policy
  code/test files. Scoped ty checks passed for model limits, catalog, proxy API
  and Claude service. This is not a claim of whole-repository type cleanliness.
- Strict validation passed for this change and all 73 main specs.
- `git diff --check` passed.

For 1M-capacity Claude models: default context 272000, maximum 1000000,
usable context 258400 (95%), default compaction threshold 244800 (90%).
For 200k-capacity models: context/maximum 200000, usable 190000,
compaction threshold 180000. Output policy is unchanged.

Separate compaction work, outside this context-metadata change:
[Source compaction context](https://github.com/DOCaCola/codex-lb/blob/main/openspec/specs/model-source-routing/context.md#complete-source-compaction-input).
