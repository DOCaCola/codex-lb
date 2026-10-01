# Verification — 2026-10-01

## Completeness and correctness

- Billing-first Claude main/helper bodies preserve system order and cache markers
  through real dispatch preparation. Missing CLI/OAuth headers and a nonleading
  billing marker do not gain native recognition.
- Native mixed exclusions expose safe counts and actual deadlines. Native Messages
  route tests verify Claude paused/cooldown explanations without identities.
  OpenRouter route tests preserve upstream 429 status and Retry-After under
  reasoning-restricted failover. Existing policy, authorization and ownership
  regression suites remain passing.
- Cache API tests distinguish complete zero observations, missing/invalid usage,
  window boundaries, deleted/internal requests and compaction. Input is normalized
  once. Unknown ratios remain null. Account-read permission is enforced.
- Conversation API tests verify source/subscription counting namespaces, separate
  lifetime/latest-seven-day scopes, visible-output TPS, unknown speed/cache data,
  errors and cancellations. UI tests verify coverage, measured values and the
  inclusion of the latest hourly bucket after JavaScript date serialization.

## Checks

- 505 backend tests passed: Claude profile/routing, routing diagnostics, native
  load balancing, request-log/report repositories, provider observability,
  OpenRouter, conversations and dashboard permission gates.
- 81 frontend tests passed: conversation details/activity, Claude cache activity,
  Reports page and dashboard schemas.
- Frontend TypeScript build, scoped ESLint, production Vite build, scoped Ruff
  and type checks of new observability/profile/service/proxy code passed.
- One Playwright regression passed across light/dark themes and desktop/narrow
  cache layouts, with actual chart rendering and no page overflow/runtime errors.
  Screenshots are generated in frontend/test-results under the test name
  `provider observability details and cache activity` (ignored local artifacts).
- Change and all 75 canonical specifications validate strictly. Specs
  were synced before archival.

## Existing baseline failures, not concealed

The broader initial backend run exposed eight older test-fixture failures in
test_request_logs_service.py and test_reports_service.py (missing cost-coverage
fields). All eight reproduce on unchanged HEAD 7d6748ceb in a detached temporary
worktree. They are not modified by this change.

Locale parity has 28 pre-existing English-only keys in each of ko and zh-CN.
The same missing key sets exist on HEAD; all new keys have all three translations.
The unchanged Claude routing line calling reasoning_allowed also has an existing
list-invariance type error. No compatibility defaults were added to hide these.

## Qualification and scope

This is synthetic/local verification, not live OAuth acceptance or cache-hit-rate
qualification. Agent LB's reported billing/cache outcome remains third-party
evidence. Verification completed before archival, commit, push or deployment.
No additional content retention or timed pause was implemented.
