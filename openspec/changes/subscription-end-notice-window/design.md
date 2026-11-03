# Design

The rule lives in the shared account summary that builds every account notice, so the dashboard card strip and
the dashboard list row stay consistent.

The running cycle ends at:

- Codex: the weekly reset; for monthly-only accounts, the monthly reset.
- Claude: the seven-day window reset.
- Antigravity: the latest weekly reset across its quota families, since the end falls inside the running cycle
  of every family whose weekly window resets after it.

A reset that is unknown or has already passed contributes no cycle, so only the three-day lead applies.
