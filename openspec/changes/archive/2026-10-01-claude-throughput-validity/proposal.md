# Proposal

## Why

Claude gateway-observed output can arrive immediately before completion, making post-TTFT throughput an unreliable estimate. A production request reported 578 output tokens over a 23 ms observation window and displayed 25,130.4 TPS. Unknown reasoning counts also prevent claiming visible-text throughput.

## What Changes

- Apply the existing OpenRouter estimated-throughput policy to Claude: total reported output, successful turns only, and a minimum one-second post-first-output window.
- Share the backend TPS expression between Reports and conversation analytics, preserving native OpenAI semantics.
- Label gateway-derived throughput as estimated and explain sample exclusion in existing UI surfaces.
- Detect nonempty redacted thinking and thinking signatures before Responses adaptation without logging their contents or inventing token counts.
- Preserve stored timings and usage; correct historical display and aggregate queries without backfilling.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: Opaque thinking timing and truthful gateway throughput.
- `proxy-runtime-observability`: Provider-specific TPS semantics across request tables, Reports and conversation analytics.

## Impact

Claude SSE timing observation, request-log/report SQL, frontend speed formatting and explanations, and regression tests. No schema, client, routing, pricing or production configuration changes.
