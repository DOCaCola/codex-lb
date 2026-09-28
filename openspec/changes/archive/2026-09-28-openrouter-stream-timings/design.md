# Design
## Context
Existing source logs accept nullable latency and first-token latency. OpenRouter
does not populate the vLLM metrics consumed by the source parser.
## Goals / Non-Goals
Measure OpenRouter only, consistently for HTTP and downstream WS. Do not change
subscription/Claude/generic source measurements, routing, retries or settlement.
## Decisions
- Derive Free/Paid/Unknown from existing key metadata, retain stale indicators,
  and use the same tier component in dashboard cards/lists and account details.
  OpenRouter documents a free-key flag, not a commercial plan identifier.
- Label compatible upstream HTTP as HTTP without changing stored/API values.
- Measure at the shared forwarding attempt using the injected monotonic Clock.
- Reuse existing parsed SSE frames; a separate content classifier recognizes
  nonempty text, reasoning and tool argument deltas. Lifecycle, role-only,
  usage-only, error and terminal snapshots are not first-token evidence.
- Start before opening upstream; freeze duration at terminal, not client drain.
  Local duration remains available without TTFT. Nonstreaming gets duration only.
- Persist using existing timing fields. Native OpenRouter's timing policy is
  gateway-observed; never mix provider TTFT with a gateway duration.
- Estimated TPS uses total reported output tokens, including reasoning because
  first reasoning output starts the clock. Require success and at least 1000ms
  after first output; apply the same rule to dashboard and report aggregation.
- Dashboard marks OpenRouter TPS approximately and explains gateway timing.
  Old null timing rows stay null; no historical reconstruction.
## Reference evidence
Inspected 2026-09-28: OpenCodex 3cc34e118192 separates estimated decode throughput
and rejects sub-second windows; OmniRoute a58000c7685f uses monotonic timing but
counts first forwarded chunks; CLIProxyAPI acdace936fa7 filters substantive
protocol events but falls back to packets/errors; Sub2API 9a62841fd124 records
first-token latency with path-dependent chunk semantics. No code copied. We
adopt monotonic observation and filtering, not fabricated first-token fallbacks.
## Risks / Trade-offs
Buffering and network effects remain in observed rates, so they are estimates.
Terminal-only responses cannot establish TTFT. No new stream read or buffering.
