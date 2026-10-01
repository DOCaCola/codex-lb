## Design

Reuse native recognition and selectors. Reasons must come from the decision that
excluded a candidate; never infer quota exhaustion from missing telemetry. Public
diagnostics contain category counts, not account IDs or credentials. Existing
status codes, affinity and retry rules remain authoritative.

Use SQL aggregates over request_logs rather than loading conversations. Claude
input_tokens is normalized total input, already including reads and writes;
therefore cache-read ratio is cached_input_tokens / input_tokens, not a second
addition of cache components. Compare two adjacent one-hour windows by source
and model. Report observed ratios and measurement coverage without declaring a
universal cache-hit target or inferred cause.

Extend the current conversation details API and dialog. Performance samples are
successful normal requests with real timing; absent measurements remain null.
Lifetime summaries keep existing scope; the activity series is bounded to the
latest seven days and labels its window. Provider source IDs count independently
of native subscription account IDs. No additional content persistence.

## Reference

Inspected aneym/agent-lb c7f83276e4c8af0d7735adb6524fc68d34a97732
(2026-10-01), MIT. Billing-first evidence: commit
3eb7c18454a805a297ce22c92eeab73da225628f; this is third-party reported
cache behavior, not independently verified upstream behavior.
