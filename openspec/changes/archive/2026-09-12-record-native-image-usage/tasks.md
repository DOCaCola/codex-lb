## Implementation
- [x] Introduce shared native image accounting and wire dispatch, logging and settlement.
- [x] Add route-level cost and usage regressions, including missing usage and failures.
- [x] Verify relevant suites, lint, typing and specifications.

## Verification evidence
- Native accounting matrix and unrestricted-key round trips: 16 passed.
- Full Images surface and selected control regressions: 101 passed.
- Related settlement, upstream transport, translation, request-log and realtime suites: 195 passed.
- Native-focused suite before the explicit-zero additions: 43 passed.
- make lint, ty check and git diff --check passed; 65 main specifications passed strict validation.
- No pricing rates changed. No backfill, live generation, production deployment, commit or push performed.
