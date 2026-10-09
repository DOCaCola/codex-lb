# API chart restoration follow-up — 2026-09-30

API-key lifetime breakdown rows and API cost-trend tooltip values now use the
existing compact formatter. A partial $44,248.05 subtotal no longer appends
known/incomplete qualifiers or request-count strings to its chart value.
API-key bars and percentages are restored as shares of recorded estimated cost,
even with unpriced, unmetered or historically unknown request coverage. The
subtitle states this basis in all three supported locales. Unknown/free/no-usage
classification and accounting fields are unchanged. Other report comparison
guards and detailed report coverage are outside this follow-up.

- 28 frontend tests passed across API overview, trend tooltip, APIs page,
  API-key table and shared cost-coverage formatting.
- Overview regressions assert 100% single-key and 75%/25% multiple-key bars,
  including incomplete and historically unknown coverage, without inventing
  prices for unknown-only keys. An all-unknown total remains Unknown.
- TypeScript check, production frontend build and scoped ESLint passed.
- Playwright regression passed at desktop and 390-pixel mobile widths; both
  chart screenshots were visually inspected and show bars and compact percentage
  labels without horizontal overflow. Rendered bar widths are asserted as 75%
  and 25%. The mocked mobile footer was avoided by centering the panel.
- Strict change validation, all 73 main specs and diff whitespace checks passed.
- Main spec and context are synced. No backend changes are included. These
  checks qualify the local implementation; release status is verified separately.
