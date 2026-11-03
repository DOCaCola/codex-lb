# Design

## Decisions

Membership and fetching are separated in the refresh scheduler. Every account
except a deactivated one is a member, so its plan and last-known catalog stay in
the snapshot through quota, rate limits, pauses and re-authentication. Fetches go
to members that may be contacted with usable credentials; paused accounts and
accounts awaiting re-authentication keep their retained catalog through the
registry's existing carry-over path. The registry parameter is renamed from
`active_account_plans` to `member_account_plans` to match.

The registry orders `models` and the retained metadata by priority, then slug.
Carried-over plans are merged before refreshed ones, so without a fixed order a
failed fetch for one plan reorders equal-priority models.

## Alternatives

Filtering by availability when serving `/models` would move the dependency
rather than remove it. Freezing the catalog entirely would hide genuine upstream
changes; membership changes and fresh fetches still update it.

## Risks

A model available only on an exhausted or paused account stays listed. A request
for it fails with the usual no-available-account or quota error until the
account recovers, which is the same result as for any other model on an
exhausted pool. Deploying changes the served order once, which costs one cache
write per conversation.

## Migration

None. The next refresh after deploy applies the membership rule.
