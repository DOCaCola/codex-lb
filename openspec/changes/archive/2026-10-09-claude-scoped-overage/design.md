## Decisions
Return a tuple of typed restrictions rather than a single mutually exclusive scope.
Explicit rejected shared windows take account scope. Overage-only evidence plus
healthy shared windows takes requested-model scope. Healthy means allowed or
allowed_warning; when one status is omitted, require valid finite nonnegative
utilization below one and the other explicitly allowed. Ambiguous unified refusal
remains account-scoped. Structured credits_required identifies a model entitlement
restriction; it never overrides explicit shared rejection. Fast-mode refusal stays
outside automatic quota failover.

A finite 7d_oi utilization at or above one also establishes model-window exhaustion,
as in Sub2API, without requiring a status header. This does not mark shared windows
exhausted or guess which other model families share that special window.

Mixed evidence produces both scopes. Each uses its own reset; Retry-After and
aggregate reset apply only to the scope identified by representative-claim, or
the sole unambiguous scope. Missing attributable deadlines use existing 60-second
default. Never use a special-model deadline for a shared restriction. Model
restriction targets the requested model, not an inferred model family.

Persist all restrictions in one transaction, extending existing deadlines only.
Do not clear existing account restrictions or rewrite historical ambiguous rows.
No quota billing, credential health, send-budget or resource-owner policy changes.

Reference snapshots: CLIProxyAPI acdace936fa7 (fixes 44eaef0009f8 and 1cce9325738f,
issues 5915/5920); Sub2API 9a62841fd124 (credits fix 222181efd6be). Adapt conservative
classification and sibling-model tests from the former, independent simultaneous
restrictions from the latter. Unlike CLIProxyAPI's workaround, retain attributable
Retry-After for the model because our schema keeps scope and deadline together.
No source copied; source/tests inspected, not independent live OAuth qualification.
