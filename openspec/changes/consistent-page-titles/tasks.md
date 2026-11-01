## 1. Implementation

- [x] 1.1 Add a shared `PageHeader` (title, optional muted meta, right-aligned actions).
- [x] 1.2 Use it on Dashboard, Logs, Reports, Providers, API Keys (including the no-access state) and Settings.
- [x] 1.3 Remove the Reports toolbar title, the Settings icon and subtitle, and the unused subtitle strings.

## 2. Verification

- [x] 2.1 Tests cover the title on Logs and the Settings header without a subtitle.
- [x] 2.2 Typecheck, lint, frontend tests and `openspec validate consistent-page-titles --strict`.
- [x] 2.3 Rendered check of all six pages.
