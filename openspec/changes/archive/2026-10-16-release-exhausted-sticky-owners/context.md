# Context

## Incident (2026-10-15, UTC)

- Plus `481eeeda…_adf83bdb`, routing policy burn-first: primary 100% from 16:44:09 to its reset at 17:00:29
  (`reset_at` 1792083629), secondary 16%.
- 16:58:15 `ws_79a3edc26f324e90b990d73c099fc12e` (`first_turn`, `sticky_kind=prompt_cache`, `capacity_weighted`)
  selected Plus; the 16:58:16 usage snapshot still showed 100%. The reattach was pinned to Plus
  (`replay_required_account_id`) and produced `continuity_fail_closed … owner_account_unavailable`.
- Plus served no requests between 16:44:30 and 16:58; whether its status was blocked in that window is not established.

## Code path before the change

- `budget_pressured` was true (primary 100 > 95) but `burn_first_reallocate` is false for a burn-first owner, so
  `not (budget_pressured and burn_first_reallocate)` kept the owner via `select_account([pinned])`, which checks status,
  cooldown and backoff only.
- Even when released, `_select_account_preferring_budget_safe` picks from the burn-first pool first, and plain
  `select_account` ranks burn-first ahead of usage.

## References

- opencodex `src/codex/routing/cache-affinity.ts` `mayRebindAffinityForQuota`: keep the binding through threshold
  crossings, release it at ≥100% or when unusable.
- sub2api `tryStickySessionHit` / `shouldClearStickySession`: clear when rate-limited, unschedulable or over threshold;
  a 429 with a window at 100% blocks the account until that window resets.
- CLIProxyAPI: rebinds on quota or 429.
- agent-lb: `hold_sticky_until_exhausted` with `_usage_exhausted` (≥100), drain strategies only.

## Constraint

`account-routing` "Foreground routing treats local usage snapshots as non-authoritative": local 100% may rank but not
reject. Exhaustion is evaluated on the latest snapshot without a reset-time check, matching the existing threshold
checks; the usage refresher replaces the snapshot after a reset.
