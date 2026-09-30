## Decisions
Use the successful retained usage snapshot as evidence of reported windows. Omit null scoped windows only when usage and its successful observation timestamp exist. Initial metadata failure remains unknown; known scoped windows remain visible when stale, expired or temporarily invalidated by reset barriers. No plan-tier inference or substitution with shared utilization.

Add nullable resets_at to ClaudeQuotaHistory and persist it transactionally from API/header observations. Old rows keep null; never backfill from the current deadline. Preserve thirty-day retention and seven-day hourly observed quota averages.

Extract the existing Codex scheduled-remaining scalar formula into core usage pacing. Claude derives a separate guideline using its seven-day duration and each recorded reset deadline. Begin at the actual observation, not its earlier hourly bucket. Stop at expiry or a subsequent null deadline. Break the line at changed deadlines, including unexpected resets, and do not project historical cycles backward or invent future reset cycles. Normalize deadlines to whole seconds for API/header subsecond timestamp precision, without changing the stored evidence.

Reuse AccountSeriesChart, its dashed Line, native weekly color and legend. Explicit series styling travels through the provider API/schema; ordinary series remain measured hourly values with gaps. OpenRouter remains request-count-only. Explain that Weekly plan is an even-consumption guideline, not provider-reported quota or replenishment.

## References
Inspected 2026-09-30 using Sep29 snapshots: OpenCodex 8a005dd98 creates scoped rows only when reported; Sub2API 9a62841fd conditionally renders Sonnet; OmniRoute 113de57b includes only valid normalized windows. No equivalent Claude pacing guide was identified in these or CLIProxyAPI d33f63f8. Reuse our native Codex calculation, not a copied third-party chart.

## Verification
Cover successful null windows versus initial/error/stale/expired states, transactional reset persistence, legacy migration upgrade/downgrade, scoped chart reads, no prehistory, absent deadlines, expiry and same-hour reset transitions. Verify unchanged Codex pacing and OpenRouter units, shared colors/dashes, frontend build and desktop/mobile screenshots. No live upstream requests required.
