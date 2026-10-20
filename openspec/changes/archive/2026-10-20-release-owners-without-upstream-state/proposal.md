# Release Owners Without Upstream State

## Why

A resumed thread's first HTTP turn on DOCa Plus failed upstream with `server_error` after `response.created`. The durable bridge row
kept DOCa Plus and the turn state but no response anchor, and the turn-state alias created a hard `codex_session` sticky
row on DOCa Plus. The failure put DOCa Plus into error backoff. Every client retry carried that turn state, so both
records required DOCa Plus, selection failed with `hard_affinity_saturated`, and the client looped on
`previous_response_owner_unavailable` without another account ever being tried.

The archived change `2026-10-20-move-unanchored-http-turns-off-unavailable-owner` tried to recover through account-neutral replay. Production showed it never
applied: Codex input carries account-scoped client metadata, so replay validation rejected it with
`account_scoped_input`.

Ownership is established by a completed response (the sub2api model). Without one, the account holds nothing a request
without `previous_response_id` depends on: the client sends its complete input.

## What Changes

- An HTTP-bridge request without `previous_response_id` on a durable row without a response anchor no longer requires or prefers the
  row's account. The bridge tells selection that the owner holds no upstream state, so a hard `codex_session` row for
  that conversation acts as a preference: a healthy account keeps the turn, and an account that cannot serve it loses
  the turn and the row.
- Port upstream PR #2486 (with #2627): a hard continuity owner blocked only by its own transient error backoff is
  admitted instead of failing the turn. It applies only when the narrowed account is an ownership constraint; a soft
  preferred account in backoff still falls back.
- Revert `810c50cf0` (account-neutral replay of unanchored rows) and its spec text.

## Capabilities

### Modified Capabilities

- `sticky-session-operations`: unanchored rows are not continuity owners; hard owners are admitted during their own error backoff.
- `proxy-admission-control`: an unanchored fork row names no preferred account.
- `responses-api-compat`: verified full resend recovery no longer includes the unanchored-row exception.

## Impact

- `http_bridge/streaming.py`, `affinity.py`, `service.py`, `load_balancer.py`, the sticky and unbound selection paths and
  `balancer/logic.py`.
- No setting, migration, dashboard or API schema change.
