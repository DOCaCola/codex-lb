# Quota reset notification context

This opt-in feature reports observed native OpenAI/Codex quota replenishment. It
does not infer an upstream business reason, monitor OpenRouter balances, or change
account routing. Each account/window transition produces an independent event.

## Detection

Fresh usage refreshes establish the first baseline without notifying. A crossed
reset deadline plus replenished quota is scheduled. A drop of at least five
percentage points before the deadline is unexpected, including unchanged deadlines;
ordinary rolling deadline drift is excluded. An 80% → 0% used transition before
the weekly deadline therefore emits an unexpected reset.

Observation timestamps are captured before fetching, so late older fetches cannot
overwrite newer baselines. Missing windows invalidate their baseline while keeping
an ordering watermark. Reappearance and identity, plan, or duration changes start
fresh comparisons. Disabling or editing configuration clears baselines; historical
usage is never replayed as notifications.

Known reset-credit consumption records intent before the upstream operation,
clears affected baselines and suppresses detection for ten minutes. This includes
all local seats sharing the upstream workspace identity. Failed consumption can
therefore conservatively suppress a real reset. Out-of-band redemption cannot be
distinguished from other unexpected replenishment. Polling cannot observe a reset
that is fully consumed again between observations.

## Delivery and failure modes

Baseline advancement, usage history and durable outbox insertion share a transaction.
PostgreSQL relaxed telemetry commit durability is not used when the webhook is
enabled. SQLite writer serialization and a PostgreSQL configuration-row lock
protect concurrent observations and claims. No database transaction spans HTTP.

Workers claim with a 45-second lease, use a ten-second HTTP timeout, and retry
network failures, HTTP 408/429 and 5xx. Delivery is limited to four attempts within
15 minutes; delays use exponential backoff starting at five seconds and respect
Retry-After up to 300 seconds. Crashes after successful transmission can cause
duplicates, so receivers must deduplicate event IDs. Permanent failures are visible
in settings; this is bounded best-effort delivery, not an unlimited message queue.

Pending work is capped at 1000 events; overflow logs a sanitized warning. Delivery
records expire after seven days. Configuration changes cancel queued/claimed
old-generation events; an HTTP request already in flight cannot be recalled.

Destinations may use HTTP or HTTPS, without URL credentials or fragments. Private
and loopback addresses are allowed with normal DNS resolution. HTTP is unencrypted;
operators are trusted to choose reachable destinations. Redirects, proxy
environment variables and cookies are disabled; TLS verification remains enabled.
Receiver bodies and sensitive URLs are never read into diagnostic logs.

## Reference evidence

Source inspection, not independent live-provider verification:

- OpenCodex `e70b3d8`, `src/quota/reset-{detector,observer,sinks}.ts`: observation
  baselines, scheduled/surprise classification and five-point threshold.
  https://github.com/lidge-jun/opencodex
- OmniRoute `86870a82`: signed generic HTTP delivery, retry and test/status concepts.
  https://github.com/diegosouzapw/OmniRoute

Inspected for this change on 2026-09-26. No implementation was copied wholesale.
