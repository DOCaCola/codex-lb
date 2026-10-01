# Design

Store typed non-secret subscription metadata separately from rotating credentials.
Explicit imports seed it, bootstrap success replaces it, and refresh/reconnect must
not discard retained observations. Resolve known exact plan identifiers with the
specific Max rate-limit multiplier taking priority over generic subscription type.
Unsupported identifiers stay unknown rather than guessed from usage or pricing.

Add subscription as an independent metadata endpoint with six-hour successful
cadence, existing durable claims, generation fencing, timeout and Retry-After
cooldowns. Validate bootstrap's account/organization against the enrolled identity
before persisting. Failures retain last-known data and expose a diagnostic, never
affecting inference health, quotas or account eligibility. Existing accounts are
discovered by the ordinary scheduler without reimport. Manual refresh uses the
same endpoint machinery. No special calls are added to inference.

Expose a normalized planType plus retained metadata, timestamps and diagnostic.
Reuse current account subtitle formatting for cards, lists and details. Include
the plan in account search; preserve all existing quota/model/routing controls.

Capture the derived plan in PreparedClaudeRequest after final account validation,
and carry it through SourceDispatch to the existing request-log plan_type column.
Each retry gets its own selected-account snapshot. Do not query current metadata
at completion or backfill historical requests with an unverifiable current plan.
Tables and request details use localized Claude plan labels, with absent historical
snapshots remaining absent.

Reference: OmniRoute dbe703a0000b303cd7b1cf5879cb8740e5bfce71,
open-sse/executors/claudeIdentity.ts and ProviderLimits/utils.tsx (2026-10-01).
Its credential import and live bootstrap paths disagree on top-level versus
oauth_account nesting; use the typed oauth_account contract observed in its live
bootstrap path, not speculative alternate-shape parsing. Source inspection does
not establish OAuth eligibility for Free accounts.
