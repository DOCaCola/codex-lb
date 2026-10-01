# Tasks

## 1. Model-cell presentation

- [x] 1.1 Separate identity and muted metadata, hiding default tiers without parentheses; add table regressions for catalog names, titles, effort/tier combinations and requested-tier differences, and sync spec/context.

## 2. Integration

- [x] 2.1 Verify responsive light/dark browser screenshots, focused frontend tests, typecheck, lint and strict OpenSpec validation.

## Verification

- 121 focused frontend tests passed, including effort/tier combinations, actual
  tier selection, requested-tier differences, catalog names and exact-ID titles.
- Six light/dark browser cases passed at 320, 390 and 1440 pixels, including a
  computed-color check against the existing muted operation label. Desktop dark
  screenshot inspected; no horizontal document overflow.
- Typecheck, changed-path ESLint, frontend production build, diff checks and
  strict change/frontend-architecture validation passed. Specs/context synced.
- No commit, archive or deployment performed.
