## Context

The research for this change lives outside the repository (`antigravity-integration-design.tmp.md`, 2026-10-29). It captured the real agy CLI 1.4.10 against an isolated TLS mock and compared CLIProxyAPI 90c447d, OmniRoute b1903111, opencodex d844ff4 and sub2api a3298b4. This document records the decisions that shape the code.

## Decisions

**Module shape.** `app/modules/antigravity` is a sibling of `app/modules/claude`, backed by a `model_sources` row of kind `antigravity` plus an `antigravity_accounts` row. It plugs into the same seams as Claude: a translated attempt inside `_dispatch_source_responses_attempt`, a provider recovery loop, the source WebSocket bridge, the scheduler and a dashboard router. It does not depend on Claude naming, errors or wire identity.

**Identity.** Only the CLI identity is used (Argon is CLI-only; mixing CLI and IDE identities on one account is a fingerprint the native client never produces). The version record pairs version and changelist atomically because the changelist is a build property; a fresh install starts from the seeded lab record (1.4.10 / 1009308193). The platform defaults to `darwin/arm64`, a common real install, and is an operator setting.

**Session and conversation identity.** The native CLI sends one signed-int64 `sessionId` per installation across conversations, so each account gets one random persisted value. Conversation identity goes into `cascade_id`/`root_cascade_id` labels and the request ID, derived from the Codex conversation, so nothing local is keyed on `sessionId`.

**History labels.** The captures show `used_claude`/`used_claude_conservative` as installation history: false on the CLI's first Claude turn and true on every later request in any cascade, whatever its model. `used_non_gemini_model` is true on every captured agent request, Gemini included, because each CLI turn first sends a Claude checkpoint request. An account is our installation, so it persists a `used_claude` flag set by its first Anthropic-wire dispatch. OmniRoute strips these labels (#16618), but only for a passthrough harness that set its own and alongside a prompt rewrite; that is no evidence against the native values.

**Signatures without a server store.** Codex already resends encrypted reasoning items. Gemini thought signatures are sealed into those items with the dispatching account, project, family and client scope, the same way Claude signed thinking travels. The existing source continuation materialises `previous_response_id` history, so no extra replay table is needed.

**Quota.** The summary reports per-family 5-hour and weekly fractions. A family is blocked when either window is exhausted; routing ranks by the binding (lower-remaining) window. Reported quota errors add a family cooldown until `quotaResetTimeStamp`/`quotaResetDelay`, because summary telemetry lags.

**Retries.** The native CLI retries 503 without limit and never refreshes on 401; Codex and Claude Code clients have their own retry loops, so proxy retries are single and bounded, and never follow delivered output.

**Verification.** A `VALIDATION_REQUIRED` 403 cools the account down for 15 minutes and keeps the verification link on the account for the operator. OmniRoute measured these responses as transient on healthy accounts, so they do not disable the account.

**Chat Completions.** Chat requests for Antigravity models use the shared translating-adapter branch: Chat controls are validated and mapped as for Claude, then the request goes through the Responses wire. Chat clients drop reasoning items and Antigravity has no Chat replay store, so an unsigned Gemini tool call carries the skip-validator sentinel and an unsigned Claude-wire tool turn continues with thinking off; both paths already exist in the protocol.

**Risk posture.** Google names third-party use of the Antigravity login as grounds for suspension. New accounts start paused, bans are permanent state, and background traffic is limited to what the CLI itself sends (loadCodeAssist, fetchAvailableModels, retrieveUserQuotaSummary).

## Failure modes

- Manifest or archive unavailable: keep the verified record, show the error; inference continues.
- Token refresh rejected with `invalid_grant`: account becomes `reauth_required`.
- Project missing after onboarding: account stays `misconfigured` with the onboarding error.
- Every account blocked: quota-only blocks return 429 `usage_limit_reached` with the earliest reset; other blocks return 503 with diagnostics.

## Example

A Codex turn for `antigravity/gemini-3.8-flash` with effort `medium` on conversation `c1` selects the sticky account, sends model `gemini-3.8-flash-medium` with request ID `agent/<uuid5(c1)>/<ms>/<turn uuid>/0`, the account's session ID and the account project, and streams Responses events back. A later `QUOTA_EXHAUSTED` cools the Gemini family on that account until the reported reset and moves the next turn to another Pro account, which receives the sentinel instead of the old signatures.

## Open items (operator qualification)

VALIDATED tool config for Claude entries, catalog effort fields, HTTP/2 wire, Argon/Flash quota coupling on Ultra and cache behaviour across an account move can only be confirmed against a real account and are out of scope for automated tests. The same holds for:

- the server-side meaning of the `used_*` labels (we replicate the 1.4.10 capture values);
- signature placement for Claude-on-Antigravity;
- acceptance of `pattern` and of array `items` in compiled tool schemas, and of `responseJsonSchema`;
- the server-side meaning of verification responses.

Out of scope for this change: hosted `web_search` is not offered on Antigravity models; request logs carry no API-equivalent cost because there is no Gemini price table; the dashboard pooled quota rings and weekly pace stay Codex/Claude-only; ban notifications use the existing account state, not the quota webhook; subagent lineage is not projected into the native labels.
