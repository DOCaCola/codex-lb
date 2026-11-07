## 1. Events

- [x] 1.1 Builder that turns account summaries, subscription ends and pool paces into time-ordered events
- [x] 1.2 Merge rules: account back absorbs its pool reset; simultaneous events of one kind and pool share a row
- [x] 1.3 Unit tests for the builder

## 2. Dashboard

- [x] 2.1 "Coming up" section between Accounts and Activity with a 24h / 7d toggle stored in the browser
- [x] 2.2 Rows with time, countdown, tone, provider, linked account names and impact; day headings for 7d; "Show all"
- [x] 2.3 Shared credit amount and short time formatters
- [x] 2.4 Locale strings for English, Korean and Simplified Chinese

## 3. Verification

- [x] 3.1 Component and page tests
- [x] 3.2 Frontend lint, tests and build; `openspec validate --strict`
