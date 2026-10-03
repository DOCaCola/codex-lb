## Decisions
Thread message identifiers use a distinct resource-key namespace, scoped by API
key and model. Persist ownership before exposing the response message ID and
reuse the existing provenance TTL and admission checks. Do not retain content.
Missing provenance returns native HTTP 404 with the `thread_not_found` code and
message marker, allowing the client to replay complete history.
An unavailable owner returns the same replayable 404, with a message naming the
unavailable account rather than missing state: Claude Code holds the thread's
full history, so replay moves it losslessly, whereas waiting can block the
conversation until a weekly reset. This also overrides the native recovery
rule that otherwise returns the owner's original refusal. A continuation that
also carries server-tool resources keeps the existing refusal, since replay
would still be bound to the owner. Owner refusals still record cooldowns.
CLIProxyAPI PR #6347 likewise uses `thread_not_found` as the replay signal
whenever the gateway cannot continue a thread. Bare upstream 404s are normalized
only for an actual thread continuation and an explicit missing-thread code or
observed wording.
Native requests retain their tools and cache markers, so no alias map is needed.

## Qualification
Route tests cover streaming/JSON ownership, expired and foreign scope, no
cross-account retries and missing-thread errors. An isolated Claude Code/mock
test must establish automatic full-history replay without production traffic.
