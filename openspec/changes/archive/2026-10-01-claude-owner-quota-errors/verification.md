# Verification

## Completeness

All four implementation tasks are complete. The modified Claude pool exhaustion requirement is synced to the main specification and its rationale is recorded in the capability context. The change remains active, not archived.

## Correctness

- 35 targeted tests passed: HTTP Responses (both endpoint families), native Messages/count_tokens resource owners, real downstream WebSocket turns, retained continuation replay, unknown timing, mixed barriers, excluded candidates, multiple quota windows, post-reset same-owner selection and ceil-rounded error timing.
- 407 related tests passed: Claude routing, quota failover, auth recovery, overload, capacity, resources, inference, Chat, search/tool context, replay, credentials and WebSocket transport cleanup.
- No upstream sends occur for locally blocked owners despite a healthy alternate. Retained logical input/output and resource ownership survive refusals. Consecutive quota errors do not close the WebSocket.
- Changed Python files pass ruff lint and format checks; git diff --check passes.
- Strict validation passes for the change and all 75 main specifications.

## Coherence and qualification

The selector owns classification; ClaudeError supplies typed public detail; existing HTTP and WebSocket boundaries retain their response shapes and safe headers. Last upstream refusals and admission/settlement budgets remain unchanged. No client changes, migration, configuration change, commit, push or deployment was performed.

Typing check of credentials.py and proxy/api.py passes. Including routing.py reports the existing invariant-list mismatch at reasoning_allowed (list of reasoning literals versus list[str]); a temporary unchanged HEAD copy reproduced the same sole diagnostic. No new typing diagnostic was introduced; the unrelated signature was not changed.

Gateway protocol mocks verify these contracts. They do not establish that the live Codex client sleeps until reset or resumes automatically. That remains a client behavior qualification, not a promise made by this change.
