## 1. Implementation

- [x] 1.1 Add `CountdownKind` (cooldown, expiry) to the countdown formatter; quota resets use cooldown, reset-credit expiry uses expiry.
- [x] 1.2 Notices carry the kind with their end time; exhausted windows are cooldowns, subscription ends are expiries.

## 2. Verification

- [x] 2.1 Formatter and notice tests cover both kinds.
- [x] 2.2 Typecheck, lint, frontend tests and `openspec validate cooldown-countdowns-keep-hours --strict`.
