## Why

A reset-credit redemption from the dashboard Reset button or `/v1` reached the
webhook as an unexpected reset. Only the usage-limit consume path recorded the
redemption marker, and that marker suppressed the event instead of describing it.
Operators cannot tell a surprise provider reset from one codex-lb performed.

## What Changes

- Report a reset as `redeemed` when codex-lb redeemed a reset credit for the
  account between the two usage observations that reveal the reset.
- Record redemptions on both consume paths (usage-limit and banked credits),
  before the upstream call, so an ambiguous outcome is still labelled.
- Offer `redeemed` as a selectable webhook kind; existing configurations that
  receive unexpected resets also receive redemptions after upgrade.

## Impact

- Webhook payloads gain the `redeemed` kind; the payload shape is unchanged.
- Migration replaces the suppression timestamp with the redemption time.
