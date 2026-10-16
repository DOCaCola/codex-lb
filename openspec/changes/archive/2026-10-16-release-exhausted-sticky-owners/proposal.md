# Release Exhausted Sticky Owners

## Why

On 15 Oct the burn-first Plus account (`481eeeda…_adf83bdb`) reported its primary window at 100% from 16:44:09 until
its reset at 17:00:29 UTC. At 16:58:15, `ws_79a3edc26f324e90b990d73c099fc12e` (first turn, `prompt_cache` mapping,
`capacity_weighted`) still selected Plus; upstream rejected it, and the reattach, pinned to Plus because its body was
not account-neutral, failed closed with `owner_account_unavailable`.

Two rules let that happen. The sticky path releases a budget-pressured owner only when a burn-first target exists
elsewhere, so a burn-first owner itself is never released, however exhausted. And budget-safe selection takes the
burn-first pool first without looking at usage, so a released owner would be handed straight back. Strict `>`
thresholds also leave a window at exactly 100% looking budget-safe at the default 100% secondary threshold.

opencodex releases a cache-affinity binding at 100% usage; sub2api drops a sticky binding over threshold or on a 100%
429; CLIProxyAPI rebinds on quota; agent-lb holds drain stickiness only until exhaustion. Upstream codex-lb and
Frozen811 behave like ours.

## What Changes

- A soft (`prompt_cache`, `sticky_thread`, `codex_session`) owner that is not rate-limited and reports either window at
  100% is released when a non-exhausted account is selectable, under every routing strategy and routing policy. Burn-first
  therefore means "hold until exhausted". When every candidate is exhausted, the owner is kept.
- Budget-safe selection treats an exhausted account as over budget, skips exhausted accounts in the burn-first pool, and,
  when nothing is under budget, ranks non-exhausted accounts ahead of exhausted ones before falling back to the whole
  pool.
- Local usage still never rejects an account: with no alternative the exhausted account remains selectable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sticky-session-operations`: new requirement for releasing exhausted soft owners.
- `account-routing`: "Manual account routing policy" limits burn-first preference to accounts with quota left.

## Impact

- `app/modules/proxy/_load_balancer/sticky_selection.py` (`_select_with_stickiness`,
  `_select_account_preferring_budget_safe`, new `_sticky_usage_evidence` / `_state_usage_exhausted`).
- The reattach owner pin (`replay_required_account_id`) is unchanged; it is a separate continuity guard.
