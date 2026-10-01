## Implementation
- [x] Preserve imported subscription metadata and implement exact normalization.
- [x] Add independent authenticated bootstrap refresh with cooldown and ownership checks.
- [x] Display localized detected plans using existing account UI styling.
- [x] Snapshot the selected Claude plan for native/adapted HTTP and WebSocket logs.
- [x] Cover import, discovery, refresh failure, races and account UI regressions.
- [x] Verify backend/frontend checks and browser layout; sync and validate specs.

## Verification

- 199 backend tests passed: subscription normalization/discovery, request plans,
  native/adapted inference, WebSocket continuation/failover and dashboard costs.
- 207 further backend tests passed: source settlement, Claude credentials,
  metadata coordination, accounts, scheduler, routing and reset behavior.
- 447 affected frontend tests passed; final label/sorting refinements passed in
  focused reruns. Typecheck, changed-path Ruff/ty/ESLint and production build passed.
- Browser: subscription refresh Pro → Max 20×, shared list/card/details and mobile
  layout passed. Weekly-consumer dashboard checks passed at 320, 390 and 1440px.
  Screenshots inspected; provider labels say Claude without OAuth suffix.
- Both active changes and all 75 canonical specifications passed strict validation.
- Canonical Claude specs/context and user documentation synced. Reviewed and
  retained concurrent weekly-consumer cost/account-view work under this task.
- No live upstream requests, database migrations, production changes, archive,
  commit or push were performed.
