## 1. Layout

- [x] 1.1 Cards render one bottom group, pinned with `mt-auto`: the Codex credits footer (always) and a reserved status-strip slot.
- [x] 1.2 The card grid uses `auto-rows-fr` from two columns on (container query); a single column keeps natural heights.
- [x] 1.3 `ProviderNotice` carries `until`; `noticeHeadline` appends the time left in the card strip and the list row.
- [x] 1.4 OpenRouter `money` uses the en-US currency format with 2–4 fraction digits; the dashboard today cost uses `formatCurrency`.
- [x] 1.5 The reset-credit button stays in the Codex credits footer; the strip offers only Re-auth or Resume; list rows keep the reset button as their remedy.
- [x] 1.6 Countdowns show days only from three days left and always hours and minutes below one day.

## 2. Verification

- [x] 2.1 Tests cover the shared bottom slots, the zero-credit footer, the reserved slot for other providers, notice times, and OpenRouter amounts.
- [x] 2.2 Typecheck, lint, frontend tests, and `openspec validate consistent-dashboard-account-cards --strict`.
- [x] 2.3 Rendered check against live dashboard data: equal card heights, the same footer and strip positions, and visible remaining times.
