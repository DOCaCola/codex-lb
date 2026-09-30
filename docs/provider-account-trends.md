# Provider account history

OpenRouter and Claude account detail pages use the same chart presentation as Codex.
See the [specification](../openspec/specs/provider-account-trends/spec.md) and
[data semantics](../openspec/specs/provider-account-trends/context.md).

- **OpenRouter:** hourly requests over seven days, including errors, from codex-lb
  logs. It does not include traffic sent outside codex-lb or show quota resets.
- **Claude:** hourly average quota remaining for the five-hour, weekly, and reported
  Opus/Sonnet weekly windows. Missing hours are gaps. History begins with successful
  usage refreshes after installation; earlier history cannot be reconstructed.

Refreshes accumulate Claude history automatically. Changes in its quota—including
resets—are observed changes, not predicted replenishment.
Claude also shows a dashed **Weekly plan**: the same even-consumption guideline
as Codex, based on retained weekly reset deadlines. It is not reported quota,
begins at its first observed deadline and stops when the deadline expires or is
no longer known. Legacy history without deadlines has no guideline.
