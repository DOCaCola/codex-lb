# Recover From Explicitly Refused Replayed Ciphertext

## Why

Codex keeps upstream-minted ciphertext in its local history and resends it on every later turn: reasoning and compaction `encrypted_content`, and `encrypted_content` parts of tool outputs and subagent messages. When upstream refuses one of them, every later turn of that conversation fails the same way, because the client resends the same history.

Production (`request_logs`, `error_code='invalid_encrypted_content'`, all on WebSocket):

- 2026-08-18, 2 rows: "The encrypted content for item rs_… could not be verified. Reason: Encrypted content item_id did not match the target item id." These arrived before `response.created`.
- 2026-10-01, 12 rows in conversation `01a0f8a8-f16c-73e1-9f99-4866a06e01d6`: "Encrypted function output content could not be decrypted or decoded." These arrived about 590 ms after `response.created`, without output. The client failed 12 times over 7 minutes.

Proactive stripping of ciphertext produced by another account (opencodex's issuer scrub) was rejected on production evidence: cross-account replay works (50 successful WebSocket continuations right after an account move in 7 days; 17,613 later turns on another account in 22 compacted conversations, without a decryption rejection). Only an explicit refusal proves that a ciphertext is unusable.

## What Changes

- **Identities.** A refusal qualifies only on explicit upstream identities:
  - the code `invalid_encrypted_content`;
  - the message `Encrypted function output content could not be decrypted or decoded.`;
  - a message starting `The encrypted content for item ` that states it `could not be verified`;
  - a message stating ciphertext or reasoning `was not issued to this caller`.

  A generic `server_error` never qualifies.
- **Memory.** The SHA-256 digests of the ciphertext a refused request carried are kept in a process-wide store: 24 h retention, refreshed on each hit, at most 20,000 entries with least-recently-used eviction.
- **Removal.** The native sanitizer removes remembered ciphertext from every later native request:
  - reasoning items are dropped;
  - a compaction item becomes a user note saying the earlier summary is unavailable;
  - an encrypted part of a function, custom tool or agent message output becomes `[encrypted content omitted]`.
- **One retry.** A refused request is re-sent once without the refused ciphertext, on HTTP streaming, compaction, direct WebSocket and the HTTP bridge. It is retried only when the refusal arrived before output (before any response event on HTTP; pre-created or accepted-output-free on WebSocket and the bridge) and when the sent body carried newly refused ciphertext.
  - An anchored WebSocket request is re-sent as its retained full-history body.
  - The bridge follows its generic anchor rules.
  - Account health is untouched and no account is excluded; the bridge keeps the account as a soft preference.
- **Failure.** A refused retry reaches the client.
- **Checkpoint handoff.** Excluded from remembering, removal and retry; its refusals surface unchanged. Reader tasks take the operation from the request state, because the handoff marker is a context variable of the request task.
- **Account health.** The payload-rejection health rule uses the same identity list.

## Rationale and references

- sub2api `8f2cbb5` (`openai_encrypted_content_lineage.go`, `openai_gateway_request_body.go`): rejection-driven stripping keyed by ciphertext.
- opencodex `dd2bdd2` (`core-opaque-recovery.ts`): identity list, single retry, compaction note; `account-change-state.ts`: 24 h scrub retention.
- OmniRoute `dba56ba9` (CHANGELOG #16288, #14636, #16375): strip-and-retry on decrypt refusals.
- agent-lb `9418b8f` strips foreign reasoning proactively; Frozen811 `9d22321` and CLIProxyAPI `3f0cef0` only log or classify.

## Capabilities

### Modified Capabilities

- `account-routing`: encrypted-content refusals stay account neutral, are identified by the explicit identities, and are retried once.
- `responses-api-compat`: refused replayed ciphertext is removed from the retry and from later requests.

## Impact

- New `app/core/openai/encrypted_content.py` (identities, store, payload and text helpers) and `app/modules/proxy/_service/http_bridge/rejected_encrypted_content.py` (request-state helpers).
- `sanitize_native_responses_input` strips first; `stream_responses` and `compact_responses` retry once.
- The WebSocket pre-created classifier and the accepted output-free classifier (renamed `_websocket_accepted_output_free_retry_error_code`) return `invalid_encrypted_content`; the WebSocket mixin and bridge upstream events have dedicated replay branches. The bridge's generic replay sequence moved into `_replay_http_bridge_terminal_request`, and `_WebSocketRequestState.rejected_encrypted_content_replay` keeps the bridge retry on its account.
- No setting, schema, migration or API change. The store is replica-local and in memory; after a restart a conversation pays one more refusal.
