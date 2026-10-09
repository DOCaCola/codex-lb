## Context
Inspected 2026-09-29: Sub2API 9a62841fd (3-minute success cache, singleflight, jitter; historical 3ebebef95 explains stampede/429 prevention), OpenCodex 8a005dd98 (in-flight coalescing and negative cache preserving readings), OmniRoute 113de57b (independent 180-second usage cooldown), CLIProxyAPI d33f63f8 (no equivalent core quota poller). These are source/test findings, not independent live OAuth qualification.

## Decisions
Use existing generation-fenced account-state CAS for endpoint leases and deadlines. Commit claims before network; cap a logical fetch at 60 seconds and lease at 90 seconds. Manual refresh bypasses only successful cadence. Background tick stays 60 seconds; durable due checks enforce 3-minute usage/6-hour catalog cadence. A failed attempt has a three-minute default cooldown; valid Retry-After seconds/dates takes precedence. This durable Retry-After support is our improvement, not attributed to references. Preserve data and timestamps and existing stale UI; show endpoint/status/retry deadline in existing error alerts. Profile gets precise errors but enrollment is not a scheduled metadata operation. No legacy endpoint fallback, inference penalty or error-induced token refresh.

## Concurrency and failures
UUID claim plus credential generation fences completion. Cancellation leaves a bounded lease; another caller reuses stored state until expiry. Catalog projection and quota history commit atomically with endpoint state. Existing selections and concurrent header observations survive merges. No database locks held across upstream I/O. Existing JSON rows acquire default empty scheduling state without a migration.

## Verification
Exercise public refresh route, per-endpoint independence, cooldown persistence, Retry-After parsing, concurrent workers, late completion, generation changes, normal cadence, recovery and retained readings. Deploy through existing upgrade.sh only after push and local verification.
