## Billable tier resolution
`billable_service_tier(requested, observed)` ranks tiers by cost: flex 0,
default/auto 1, priority 2, ultrafast 3. The observed tier replaces the
requested one only when it is known, not more expensive, and, when cheaper,
not a `default`/`auto` echo. Without a requested tier, the observed tier is
recorded when it is not more expensive than the standard tier. `actual_service_tier`
keeps the raw echo for diagnostics.

sub2api exempts only `default`. `auto` is exempted here too: it is the
omit-equivalent value, and production shows it echoed on priority websocket
and prewarm turns, so it proves no downgrade either.

## History repair
`repair_echoed_service_tiers` selects subscription rows (no model source) with
`requested_service_tier = 'priority'` and an echoed `default`/`auto` in both
`actual_service_tier` and `service_tier`, in id-ordered batches under the
fold-state lock. Each row receives the resolved billable tier and a recomputed
cost; the cost delta is mirrored into lifetime and report rollups below their
watermarks. Hourly and demand rollups are mirrored by re-running the fold
select for the batch before and after repricing and merge-adding the negated
before rows plus the after rows, which also moves rows between hourly
`service_tier` buckets; buckets emptied by the move are removed. The settled
tier is the idempotency marker. The scheduler finishes one full repair pass per
process before resuming the missing-cost backfill.
