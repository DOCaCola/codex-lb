# Tasks

## 1. Implementation

- [x] 1.1 Share the sticky usage evidence (priority and limit-scoped fields) between the threshold and exhaustion checks.
- [x] 1.2 Release a soft, non-rate-limited exhausted owner when the pool's best candidate is neither the owner nor
  exhausted; keep it otherwise.
- [x] 1.3 Budget-safe selection: exhausted counts as over budget, burn-first pool excludes exhausted accounts, and
  non-exhausted accounts rank ahead of exhausted ones when nothing is under budget.

## 2. Verification

- [x] 2.1 Sticky tests: exhausted burn-first owner released under capacity-weighted, usage-weighted and sequential
  drain; kept when every sibling is exhausted; burn-first owner above threshold but not exhausted kept; weekly window at
  exactly 100% released at the default secondary threshold.
- [x] 2.2 Budget-safe selection skips a burn-first account exhausted on either window.
