# Design

Reuse core balancer strategy implementation via a Claude candidate adapter.
Five-hour maps to primary; the most utilized fresh shared/model weekly window
maps to secondary, including its reset. Set capacity explicitly to one normalized
unit, never a plan label. Existing eligibility handles exhausted/stale evidence.
Rank fresh complete shared-window candidates first on unbound quota strategies;
when none are complete, rank all eligible candidates neutrally with unknown
percentages and no reset hints. This is an explicit missing-data policy, not a
claim of unused quota. Round-robin does not require quota readings.

Hard owner and configured single-account target constrain the pool; conflicts
fail explicitly. Single-account target is provider-scoped. Other strategies honor
existing eligible affinity before ranking. Round-robin uses durable admission
timestamps; weighted selection is unseeded for new requests so weights actually
affect draws. Existing affinity provides continuation stability.

No RPM/session caps or inferred Claude plan multipliers. No optional manual
weight editor in this change; normalized capacity is equal for all Claude accounts.
