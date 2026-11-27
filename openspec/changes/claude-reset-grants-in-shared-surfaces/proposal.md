## Why

Claude reset grants (cedar_ember) were only reachable from a button inside the Claude usage card, and an unused grant
silently expired. Codex reset credits already appear on the dashboard card and list row, in the provider list and
header badge counts, as a "Reset (n)" action on the account page, and can be redeemed automatically shortly before
they expire. Claude grants should behave the same way. Anthropic issues differently scoped grants (a full reset, a
Fable reset that only returns Fable weekly usage, five-hour resets), so the dialog must say which one is spent.

## What Changes

- The usage read requests cedar_ember with the existing usage call, so grant availability refreshes with usage and
  needs no extra request. A malformed grant block is unknown, never zero, and never fails the usage read.
- Claude account responses carry the number of banked grants and the nearest expiry. Banked means eligible, not
  paused, with resets left and inside its validity period; at-limit and cooldown remain redemption-time checks.
- The dashboard card, list row, provider list badge, header badge and the Claude account page show Claude grants
  through the same reset button and badge as Codex credits; all open the existing grant dialog.
- Grants are labelled by the windows they clear, following agent-lb: Full reset, Fable reset or 5-hour reset, with
  Anthropic's own label shown when it differs.
- The leader's Claude metadata loop redeems the soonest-expiring banked grant within five minutes of expiry when the
  Codex "auto-redeem before expiry" setting and reset-credit polling are both enabled. Each grant and expiry maps to
  one stable operation ID, so ticks and replicas share one durable claim through the existing journal.

## Impact

- Spec: `claude-accounts`.
- Code: `app/modules/claude` (client, schemas, reset schemas, service, scheduler, new `reset_auto`), dashboard,
  provider summary, header and Claude account frontend.
- Behaviour change: installations that already enabled Codex auto-redeem will also auto-redeem expiring Claude grants.
- No migration and no new setting.
