# Design
## Native versus translated
Native first-party thinking is replayed unchanged; one-hour affinity is a
preference, not proof that thinking signatures are credential-bound. Signed
Responses envelopes retain their authenticated model/client/conversation scope
and account restrictions. Server-tool history retains existing hard ownership.
No long-lived signature ledger or migration is introduced.
When a session rebinds, a separate scoped ambiguity marker in the existing owner
table prevents native server-resource history from being attributed to its new
preferred account. Marker retention follows the active session's one-hour TTL.
It stores no resource contents. Expired/missing resource ownership remains an error.

## Routing
Eligibility and client authorization precede preference. Native retained affinity
wins if eligible, otherwise an eligible account is selected and binding updated
with compare-and-swap. A concurrent newer binding wins. Parent metadata is used
only when a child has no retained binding, within the same client/model scope.
Explicit Claude/session/thread headers and structured metadata must agree; missing
identifiers retain isolated random identities rather than guessing from content
or shared cache cohorts. Selection logs only account ID and reason.

## Recovery
Recovery surrounds opening the upstream stream or native JSON request, not body
iteration, so it cannot replay after delivery. An explicit invalid-thinking-
signature 400 allows one same-target retry. Eligible completed thinking blocks
are omitted in a deep copy; active trailing tool chains and visible content remain
unchanged. An empty resulting message or any server-tool history refuses recovery.
Count-tokens, generic errors and 429 do not recover. The first rejected attempt
cleans up before retry; the shared dispatcher settles the logical request once.
No synthetic signatures, thinking-to-text or tool-to-text degradation.

## References
Inspected 2026-09-28: OmniRoute a58000c7685f, merged PR #7906 (July 21);
OpenCodex 3cc34e118192 native domain preservation versus translated replay;
CLIProxyAPI acdace936fa7 parent affinity; Sub2API 9a62841fd124 demonstrates more
aggressive recovery not adopted here. Source/test evidence, not live qualification.
No code copied. A 30-day ownership ledger was considered and rejected.

## Limits
Resource handles remain conservative; this change does not establish their
cross-account portability. Translated envelope account/model relaxation is not
included without separate state-type qualification. No after-delivery failover,
content-derived session matching or additional retention. Live OAuth acceptance
needs separate testing; stub tests prove routing/serialization only.
