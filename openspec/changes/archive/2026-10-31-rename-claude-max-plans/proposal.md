# Rename Claude Max plans

## Why

On 2026-10-30 Anthropic renamed its consumer plans: Max 5x became **Max** and
Max 20x became **Ultra**. Prices and weekly limits did not change. Anthropic's
subscription lead explained that the "20x" only ever described the five-hour
limit. Ultra's weekly limit has been 10x Pro since weekly limits were
introduced, and verified Ultra accounts no longer have a five-hour limit at all.

codex-lb still labels these accounts "Max 5×" and "Max 20×". It also weights
a Max 20x account as 20 Pro units in every pooled figure, so the Claude weekly
pace, the weekly quota ring and the weekly pool usage reported to Codex
clients overstate an Ultra account's weekly capacity by a factor of two.

## What Changes

- The canonical Claude plan keys become `max` and `ultra`. The rate-limit
  tiers `default_claude_max_5x` and `default_claude_max_20x`, and the new
  identifiers `max` and `ultra`, resolve to them. A generic subscription type
  of `max` alone no longer resolves to a plan: before the rename it covered both
  tiers.
- Plan weights become per window: five-hour Pro 1 / Max 5 / Ultra 20, weekly
  Pro 1 / Max 5 / Ultra 10. Account responses expose both weights.
- Recorded request-log plan snapshots are renamed in place (`max_5x` → `max`,
  `max_20x` → `ultra`). Rows keep the plan recorded at dispatch; only its
  key changes.
- Labels, plan badges and dashboard subtitles use Max and Ultra.

## Impact

- Claude subscription derivation, quota weights, weekly pace, pooled client usage.
- One data migration on `request_logs.plan_type`.
- Dashboard Claude plan labels and weekly Pro-unit totals.
