## Decisions
Thread message identifiers use a distinct resource-key namespace, scoped by API
key and model. Persist ownership before exposing the response message ID and
reuse the existing provenance TTL and admission checks. Do not retain content.
Missing provenance returns native HTTP 404 with the `thread_not_found` code and
message marker, allowing the client to replay complete history. Account
unavailability retains its existing refusal semantics, rather than claiming the
upstream state is missing. Bare upstream 404s are normalized only for an actual
thread continuation and an explicit missing-thread code or observed wording.
Native requests retain their tools and cache markers, so no alias map is needed.

## Qualification
Route tests cover streaming/JSON ownership, expired and foreign scope, no
cross-account retries and missing-thread errors. An isolated Claude Code/mock
test must establish automatic full-history replay without production traffic.
