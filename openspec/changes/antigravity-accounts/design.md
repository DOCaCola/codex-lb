## Context

The research for this change lives outside the repository (`antigravity-integration-design.tmp.md`, 2026-10-29). It captured the real agy CLI 1.4.10 against an isolated TLS mock and compared CLIProxyAPI 90c447d, OmniRoute b1903111, opencodex d844ff4 and sub2api a3298b4. This document records the decisions that shape the code.

## Decisions

**Module shape.** `app/modules/antigravity` is a sibling of `app/modules/claude`, backed by a `model_sources` row of kind `antigravity` plus an `antigravity_accounts` row. It plugs into the same seams as Claude: a translated attempt inside `_dispatch_source_responses_attempt`, a provider recovery loop, the source WebSocket bridge, the scheduler and a dashboard router. It does not depend on Claude naming, errors or wire identity.

**Identity.** Only the CLI identity is used (Argon is CLI-only; mixing CLI and IDE identities on one account is a fingerprint the native client never produces). The version record pairs version and changelist atomically because the changelist is a build property; a fresh install starts from the seeded lab record (1.4.10 / 1009308193). The platform defaults to `darwin/arm64`, a common real install, and is an operator setting.

**Session and conversation identity.** The native CLI sends one signed-int64 `sessionId` per installation across conversations, so each account gets one random persisted value. Conversation identity goes into `cascade_id`/`root_cascade_id` labels and the request ID, derived from the Codex conversation, so nothing local is keyed on `sessionId`.

**History labels.** The captures show `used_claude`/`used_claude_conservative` as installation history: false on the CLI's first Claude turn and true on every later request in any cascade, whatever its model. `used_non_gemini_model` is true on every captured agent request, Gemini included, because each CLI turn first sends a Claude checkpoint request. OmniRoute #16618 removes both as part of its fix for content-gated 429s. No reference sends them and their server-side meaning is unknown, so we omit them and otherwise keep the native label set.

**Signatures without a server store.** Codex already resends encrypted reasoning items. Gemini thought signatures are sealed into those items with the dispatching account, project, family and client scope, the same way Claude signed thinking travels. The existing source continuation materialises `previous_response_id` history, so no extra replay table is needed.

**Quota.** The summary reports per-family 5-hour and weekly fractions. A family is blocked when either window is exhausted; routing ranks by the binding (lower-remaining) window. Reported quota errors add a family cooldown until `quotaResetTimeStamp`/`quotaResetDelay`, because summary telemetry lags.

**Retries.** The native CLI retries 503 without limit and never refreshes on 401; Codex and Claude Code clients have their own retry loops, so proxy retries are single and bounded, and never follow delivered output.

**Verification.** A `VALIDATION_REQUIRED` 403 cools the account down for 15 minutes and keeps the verification link on the account for the operator. OmniRoute measured these responses as transient on healthy accounts, so they do not disable the account.

**Chat Completions.** Chat requests for Antigravity models use the shared translating-adapter branch: Chat controls are validated and mapped as for Claude, then the request goes through the Responses wire. Chat clients drop reasoning items and Antigravity has no Chat replay store, so an unsigned Gemini tool call carries the skip-validator sentinel and an unsigned Claude-wire tool turn continues with thinking off; both paths already exist in the protocol.

**Risk posture.** Google names third-party use of the Antigravity login as grounds for suspension. New accounts start paused, bans are permanent state, and background traffic is limited to what the CLI itself sends (loadCodeAssist, fetchAvailableModels, retrieveUserQuotaSummary).

**Web search.** Cloud Code has no hosted search a Codex client can rely on. The CLI declares a `search_web` function and answers each call itself with a separate non-streaming `web_search` generateContent request on the same account (Google Search grounding on the catalog's search model), so the gateway does exactly that and shows the call as a hosted `web_search_call`. Running the search on the dispatching account keeps the traffic indistinguishable from the CLI and avoids routing Antigravity content to another provider; a Codex-account sidecar (opencodex) stays an option if this proves unreliable. The search model follows the CLI's rule, captured against the mock: `webSearchModelIds[0]`, else the Flash Lite tier, and no search at all without a Flash Lite tier. A search-only round continues the same response with a new upstream round, re-projected from the logical request plus the output so far, so a later client turn replays it identically. Results are sealed into an encrypted reasoning item, which keeps them off the client's visible history while letting the next turn replay the call and its function response. Search usage is not added to the response's usage: the CLI does not report it and it is billed against the account's quota, not the client's tokens.

## Failure modes

- Manifest or archive unavailable: keep the verified record, show the error; inference continues.
- Token refresh rejected with `invalid_grant`: account becomes `reauth_required`.
- Project missing after onboarding: account stays `misconfigured` with the onboarding error.
- Every account blocked: quota-only blocks return 429 `usage_limit_reached` with the earliest reset; other blocks return 503 with diagnostics.

## Example

A Codex turn for `antigravity/gemini-3.8-flash` with effort `medium` on conversation `c1` selects the sticky account, sends model `gemini-3.8-flash-medium` with request ID `agent/<uuid5(c1)>/<ms>/<turn uuid>/0`, the account's session ID and the account project, and streams Responses events back. A later `QUOTA_EXHAUSTED` cools the Gemini family on that account until the reported reset and moves the next turn to another Pro account, which receives the sentinel instead of the old signatures.

## Open items (operator qualification)

VALIDATED tool config for Claude entries, catalog effort fields, HTTP/2 wire, Argon/Flash quota coupling on Ultra and cache behaviour across an account move can only be confirmed against a real account and are out of scope for automated tests. The same holds for:

- the server-side meaning of the labels, including whether omitting `used_claude`/`used_claude_conservative` matters;
- signature placement for Claude-on-Antigravity;
- acceptance of `pattern` and of array `items` in compiled tool schemas, and of `responseJsonSchema`;
- the server-side meaning of verification responses;
- grounding quality and quota cost of `web_search` requests on real accounts.

**Dashboard quota.** Antigravity quota is per model family, and the families are separate budgets, so the dashboard shows one bar per family instead of a single ring. Pace reports the family that runs out first. Accounts are pooled in Pro units like Claude; stale or unweighted accounts are named rather than silently skewing the totals.

Out of scope for this change: ban notifications use the existing account state, not the quota webhook; subagent lineage is not projected into the native labels.
