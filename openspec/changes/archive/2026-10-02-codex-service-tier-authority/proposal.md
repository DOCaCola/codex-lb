## Why
Fast turns were billed and displayed at the standard rate. The ChatGPT Codex
backend echoes `response.service_tier: "default"` (and on some websocket and
prewarm turns `"auto"`) on turns it serves on the requested Fast tier, and the
proxy let that echo overwrite the billable tier. Production evidence over 30
days of gpt-6 traffic: priority requests with a `default` echo average 120 TPS
and 6.5 s TTFT, while unrequested default turns average 74 TPS and 8.4 s. The
echo does not describe the served tier. sub2api
(`ResolveOpenAIServiceTierBilling`) and opencodex (`responseTierAuthoritative`,
issue #2558) treat the same echo as non-authoritative.

The request log also showed Fast turns as a "Requested priority" text line
instead of a compact tier mark.

## What Changes
- One resolver settles the billable tier from the requested and echoed tiers:
  the echo may only lower the bill to a cheaper known tier, and `default`/`auto`
  echoes never prove a downgrade. All persistence and API-key settlement sites
  use it.
- Historical rows carrying an echoed `default`/`auto` billable tier for a
  priority request are re-billed by the leader's metadata scheduler, with exact
  deltas mirrored into lifetime, report, hourly and demand rollups.
- Telemetry service-tier mix reports the billable tier.
- The request log shows the billable Fast/Ultrafast tier as a grey icon next to
  the reasoning effort, names `priority` "Fast", and shows a downgrade note only
  when the billed tier is cheaper than the requested tier.

## Capabilities
### Modified Capabilities
- `responses-api-compat`: billable tier settlement and history repair.
- `api-keys`: cost accounting for echoed tiers.
- `frontend-architecture`: request-log tier presentation.

## Impact
Backend persistence and settlement, the metadata scheduler, rollup mirroring,
telemetry, and the dashboard request log. No schema migration. About 11.4k
production rows (2026-06-16 onward, recorded at about $1,149) are re-billed at
the priority rate after deploy.
