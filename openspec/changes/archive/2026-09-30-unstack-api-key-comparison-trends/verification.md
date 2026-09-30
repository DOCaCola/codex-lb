# Verification

- Regression test first failed against the original shared stack ID, then passed after its removal. It covers independent cost/token series and hiding a series without changing another's measurement.
- Eight targeted component/calculation tests passed.
- TypeScript build, targeted ESLint and frontend production build passed.
- Desktop/mobile Playwright comparison test passed, exercising all four modes, legend interactions, tooltip coverage and no overflow.
- Desktop hourly-cost and mobile hourly-token screenshots manually inspected: independent strokes and fills share a zero baseline, without stacking.
- Strict change and API-key main-spec validation passed. Main spec/context synced; diff whitespace check passed.
- No commit, archive, push or deployment performed by this implementation request.
