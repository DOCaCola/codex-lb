## Why

The Accounts page shows one account at a time beside a narrow list. Comparing the pool means clicking through every
account, and the list cards differ in height and contrast by provider. Each provider detail panel invents its own
layout, so the same setting (routing, monitoring, export, delete) sits in a different place for Codex, Claude,
Antigravity, OpenRouter and OpenAI-compatible sources. Accounts have no address, so a detail view cannot be linked,
bookmarked or opened from Logs.

## What Changes

- Rename the page to Providers at `/providers`. `/accounts` is removed without a redirect.
- `/providers` shows every account in one table grouped by provider: account, status, two limit meters with reset
  countdowns, today's requests and cost, and routing. It has search, an All / Needs attention / Paused filter, the
  existing sort modes, an Add account button, per-group add buttons and chips for providers not yet connected.
- `/providers/:accountId` shows one account: a sticky, collapsible rail of all accounts (bold names, equal-height
  entries, search, keyboard navigation), a header with name, plan, status, actions and a ⋯ menu (Copy ID, Open in
  Logs, export, delete), a state banner, and two card columns that every provider shares. Narrow screens replace the
  rail with an account switcher in the breadcrumb. An unknown ID shows "Account not found".
- Every detail shows a Last 7 days activity card (cost or requests per day, with request, cost, token and error
  totals) from the reports API. The quota-remaining trend charts stay in the Usage cards.
- API: each `dailyByAccount` entry in `GET /api/reports` carries its day's `errorCount`.

## Impact

- Affected specs: `frontend-architecture`, `reports`
- Affected code: `frontend/src/features/accounts`, the Claude, Antigravity, OpenRouter and model-source detail
  components, navigation and dashboard links, translations, `app/modules/reports`
