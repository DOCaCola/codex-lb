# Report owner quota loss on continuations

## Why

On 2026-10-28 two Pro accounts reached their weekly limits within an hour.
Every Codex conversation anchored by `previous_response_id` to one of them was
answered with 502 `previous_response_owner_unavailable`: "Previous response
owner account is unavailable; retry later." The weekly reset was six days
away, so "retry later" was false. The client recovered only because it treats
an unrecognized failure as retryable and resends the full history without the
anchor. That resend runs on any other account. The error neither named the
cause nor told the client how to leave the spent owner.

## What Changes

- When only the client's own `previous_response_id` binds a turn to its
  owner, and the owner's persisted status shows a spent usage limit
  (`rate_limited` or `quota_exceeded`), the owner-loss failure names the limit
  and its reset time. It tells the client to retry without
  `previous_response_id`.
- On the Codex-native `/backend-api/codex/responses` WebSocket route the
  failure carries `previous_response_not_found`. An unmodified Codex client
  answers that code with a full-history resend. Public routes keep their
  existing owner-unavailable codes and must still never expose
  `previous_response_not_found`.
- This applies at WebSocket connect, when the owner refuses at dispatch, and
  when a direct HTTP stream fails closed.
- Proxy-injected anchors, input-file pins and turn-state owners keep the
  generic failure, because a resend without the anchor stays bound there.
  So do authentication loss, pauses, local capacity and failed status lookups.
- Compact's existing quota-caused owner-loss check moves into the same shared
  module.

## Impact

Responses continuity error reporting on the WebSocket and HTTP stream paths.
No settings, schema or routing changes. Pool-wide exhaustion keeps 429
`usage_limit_reached` with `resets_at`.
