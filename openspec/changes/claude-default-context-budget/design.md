## Decision
Keep discovered limits as provider capability. Derive a conservative client
context in the model-source catalog mapper, not account persistence. This handles
existing projections immediately and leaves native output enforcement and account
metadata untouched. Model limits owns the 272000 default ceiling; source catalog
construction supplies the maximum, 95% effective input and 90% compaction fields.
Remove obsolete persisted derived compaction defaults from new projections; the
mapper replaces existing projections' old derived hints with current policy.

Opus at 1M capacity advertises 272000 default, 1000000 maximum, 244800 compaction
and 258400 usable tokens. Haiku at 200000 remains at 200000 default/maximum,
180000 compaction and 190000 usable. Explicit existing context settings continue
through the shared override mechanism; they do not change discovered capacity.
The 272000 ceiling is an approved operational policy aligned with the local Codex
catalog, not a measured Claude quality limit or subscription entitlement claim.
The Codex wire mapper derives its 90% compaction hint from the final working
context after explicit global overrides, so raising a context does not leave the
old default compaction threshold pinned at 244800.

## Verification
Test existing/stale metadata, smaller discovered capacities, output preservation,
provider isolation and both client model-list endpoints. Sync specs/context/docs
and validate. Do not implement compression completeness changes in this task.
