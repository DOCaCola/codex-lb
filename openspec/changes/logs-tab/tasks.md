# Tasks

## 1. Implementation

- [x] 1.1 `LogsPage` at `/logs` renders the request logs and conversations views with a segmented view toggle.
- [x] 1.2 The dashboard drops the request logs and conversations section and `buildDashboardView` no longer carries
  request logs.
- [x] 1.3 Logs is the second core navigation item; the core navigation budget is six.
- [x] 1.4 Locale keys for the Logs page in en, ko and zh-CN.

## 2. Verification

- [x] 2.1 Logs page tests cover loading, errors, refresh, the view toggle, guest and hydration fallbacks, column layout
  and conversation filters.
- [x] 2.2 Integration tests load request logs and conversations from `/logs` and confirm the dashboard issues no
  request-log queries.
- [x] 2.3 Typecheck, lint, vitest, simplicity budgets, strict OpenSpec validation.
