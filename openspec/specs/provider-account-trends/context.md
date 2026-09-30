# Provider chart context

Account detail views reuse AccountSeriesChart, extracted from the native Codex
AccountTrendChart renderer. Grid, date axis, gradients, tooltip, colors, height and
reduced-motion behavior are shared. The native wrapper keeps its existing series,
percent axis and dashed weekly plan. Provider cards use the same border, padding,
heading and legend classes as native account usage.

OpenRouter reads the last seven days of retained request logs by model_source_id.
Counts include successes and failures, exclude soft-deleted rows, and aggregate in
SQL into UTC hours. This is local gateway activity, not authoritative OpenRouter
billing or all traffic on the key. No reset, balance estimate or quota plan is plotted.
Retention/deletion can remove history; zero-filled hours mean no retained requests.

Claude records supported quota windows only after a successful provider refresh,
in the same transaction as account state. Failed refreshes do not reuse stale quota
as a new sample. History is account-bound and cascades on deletion. Old samples are
pruned at successful refresh (thirty-day retention). No migration backfill is made.
Inactive accounts may retain old rows until their next refresh or deletion, but
reads always cover only the last seven days.

SQL reads hourly averages, displayed as 100 minus utilization (clamped 0–100).
Missing observations remain null; there is no fabricated prehistory, interpolation
across missing hours, or predicted replenishment. For example a lone 30%
used five-hour observation appears as one 70% remaining point, not a full week at
70%. Weekly Opus and Sonnet are separate series when actually reported.

New quota samples retain their reported reset deadline. Old rows remain unknown;
the current deadline is never backfilled into historical cycles. Claude's dashed
Weekly plan uses the same even-consumption calculation and weekly color as Codex,
separate from measured remaining quota. For example, an observation three days
before a seven-day reset starts a 42.86% guideline at that observation, not earlier
in its hourly bucket. The guideline stops at expiration or an observed unknown
deadline and breaks on changed reset cycles. Whole-second comparison tolerates
API/header timestamp precision without changing stored evidence. It predicts
neither replenishment nor future reset cycles. OpenRouter has no quota guideline.

The provider trend contract includes explicit dashed and colorIndex fields so
optional quota series retain their native colors even when earlier rows are absent.

The charts poll once per minute while mounted, keep query keys scoped by provider
and account, and distinguish loading/error states from an empty history. Chart reads
use the existing authenticated provider-account API authorization.
