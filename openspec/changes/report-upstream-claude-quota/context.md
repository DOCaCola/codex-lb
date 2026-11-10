# Investigation, 2026-11-10

Production revision: 6f5e4b286b1ff4f373ae8fac02850c00c5d2945b.
Initial implementation base: 651b2ad77. Deployment preparation reapplied only this
change onto fork/main 6f5e4b286 in an isolated checkout, excluding the unrelated
local reports commit. Deployment requested by the user on 2026-11-10; live
client presentation remains a separate qualification task.

DOCaColaPC Investigator inspected live thread state, committed SQLite WAL and
rollout metadata read-only through Agentwire. Chat
01a105aa-8898-7222-89c5-3d31191961fb, turn
01a1c304-e986-75c3-b545-b3e0d1ad1573, remained inProgress without outstanding
tool work. Current executable reports Codex 0.167.0-doca; the rollout's 0.160
version belongs to historical session creation. Desktop package is
OpenAI.Codex_26.1103.4239.0_x64__2p2nqsd0c76g0.

The last completed response was resp_msg_011CgtNhPddiieudxhszLHND. Production
records it at 01:27:58.052542 UTC and the next exact-chat WebSocket attempt,
ws_src_5657440eed694470b6ad6196c2d71de1, at 01:27:58.622306 UTC. That attempt
failed with upstream 429 rate_limit_error. Its account restriction was recorded
with retry_after evidence. A separate later preflight rejection reported a
five_hour recovery at 03:40 UTC; this second request is not independently tied
to the target chat.

The client's responses_retry warning at 01:27:57.849258900 UTC reports retry
1/15 after 7920.9984458 seconds, implying wake at 03:39:58.847705 UTC. Clock
skew between server and PC is approximately one second. The exact last response
ID agrees across both sides. The client had completed its tools and was waiting
on a server-advised retry, rather than an outstanding generation or tool.
The raw failed request headers were not retained locally.

Peer source inspection at 262d1c69c670c5bdcc131c8b51e59eedf7f48da1 found
core/src/responses_retry.rs:145-173 sleeping until the retry advice deadline,
and protocol/src/error.rs:426-489 retrying RetryLimit only with server advice.
The first retry notification can be suppressed in release builds while session
WebSockets are enabled; the affected session's fallback state is unknown.

The gateway already translates local quota admission failures to
usage_limit_reached, but its upstream Claude error projection handled only
prompt overflow. This change reuses classify_refusals to recognize known quota
windows and projects them into the same Responses contract. Unknown throttling
and entitlement-only errors keep their existing classification. Default
cooldowns are never presented as observed reset deadlines. Failover, ownership,
status and retry headers remain governed by their existing paths.

For example, a five_hour upstream refusal with a two-hour reset now returns
429 with error.type usage_limit_reached and integer reset metadata; a 429 with
only requests-remaining=0 continues to report rate_limit_error. Native Messages
retains the provider's error dialect.

Fresh reference inspection on 2026-11-10 used GitHub API-resolved HEAD revisions
and raw files pinned to those revisions. This is source evidence, not live
qualification. No reference code was copied. The Codex client source revision
above was supplied by the local investigator.

- lidge-jun/opencodex at 7877b6417f943d65e17523efe8298181480bfd28:
  src/bridge/errors.ts:152-168 explicitly formats spent usage windows as HTTP
  429 usage_limit_reached, with optional integer resets_at and retained
  Retry-After. Its comment explains that Codex stops instead of backing off.
  src/server/responses/core-errors.ts:158-163 uses this for final usage-limit
  refusals outside combo attempts and keeps ordinary throttling retryable.
  This directly supports the proposed client-facing error contract; it does
  not establish that every upstream Claude path is classified identically.
- router-for-me/CLIProxyAPI at 6db7d4b839d86c5b24e17bbe73bcd4db18ef1b1a:
  internal/runtime/executor/claude_executor_request.go:885-908 preserves the
  upstream body and parsed retry deadline while distinguishing credential-wide
  unified quota rejection, model throttling and fast-mode entitlement failures.
  This classifier alone does not establish a Codex terminal error projection.
- diegosouzapw/OmniRoute at 8e72dbf546f2674da4e1ae9073ad4d4b65b836f0:
  open-sse/executors/rateLimitIntraRetry.ts skips immediate same-account retries
  when the upstream hint exceeds four seconds. claudeQuotaFailure.ts records
  quota exhaustion with account/model scope and reset-based cooldown. The
  four-second threshold is not a cap on client Retry-After.
- Wei-Shaw/sub2api at ee58c0013c76ccd3f36439881bc848d342ec1c9d:
  backend/internal/service/ratelimit_service.go tracks Anthropic window resets.
  openai_gateway_responses_anthropic_native.go:133-140 attempts failover and
  otherwise uses a generic server_error response in the inspected branch.
- aneym/agent-lb at 2d903749a2fa1fb568d40d08ac11e8f0c08e68e2:
  app/modules/proxy/anthropic_rate_limits.py retains quota/reset metadata for
  routing. This establishes deadline handling, not equivalent Codex terminal
  error behavior across its routes.
- Frozen811/codex-lb at 9d22321892602f2a762e166894bc63a7a74aa41b:
  inspected tree has no equivalent Claude/Anthropic provider implementation.

Together these support two separate responsibilities: preserve true quota
deadlines for account scheduling, and project known exhaustion into the client
protocol's terminal usage-limit error. Gateway cooldown or failover alone does
not prevent the observed Codex retry sleep.

Validation: 64 focused tests passed, including 16 new transport cases and four
existing overflow/throttling regressions; make lint and the changed transport's
ty check passed. The strict delta validates; the synchronized main spec is valid
with pre-existing requirement-length warnings.

The peer verified the client source contract at the revision above:
codex-api/src/api_bridge.rs:202-236 recognizes error.type=usage_limit_reached;
endpoint/responses_websocket.rs:704-773 unwraps status-bearing WebSocket errors
into the same HTTP mapper. api_bridge_tests.rs:115-162,592-635 and
protocol/src/error.rs:426-470 establish that UsageLimitReached has no retry
delay even with retained server Retry-After. plan_type and code are not required;
resets_at is integer seconds. The installed executable contains the relevant
markers. This is source/test and binary-marker evidence, not a live probe of
the affected binary. Live target recovery and corrected error presentation
remain to be observed after deployment. The existing sleeping turn was not
canceled or modified during investigation.

Additional peer verification at 03:11 UTC: an isolated Rust parser fixture using
the production UsageErrorResponse/UsageErrorBody and wrapped WebSocket structs
accepted the exact proposed envelope, including absent code/plan_type, integer
resets_at, additional resets_in_seconds, and a 7921-second Retry-After header.
The fixture substituted serde_json::Value for the absent PlanType field and
does not validate plan enum values or execute the installed client. Source
model-provider-info/src/lib.rs:499 disables lower HTTP retry_429, allowing the
shared usage-limit classifier to determine retry behavior.

The peer's broader codex-api test attempt did not execute tests: linking hit
Windows LNK1140 PDB limits, then rebuilding without test debug symbols exhausted
D: disk space. Only the newly created target/debug artifacts were removed,
restoring 4.602 GB free. These attempts are not counted as passing tests. The
isolated parser fixture passed; the running target, credentials and configuration
remained unchanged.
