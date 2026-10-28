# Move Model Admission Limits To Another Account

## Why

Since 2026-10-25, upstream has occasionally refused a turn with HTTP 429 `rate_limit_error` code
`turn_rate_limit_exceeded` ("Codex is at capacity, please try again later") and a `Retry-After` of seconds to minutes
(CLIProxyAPI #7017 observed 8–515 s). The refusal applies to one model on one account while that account's quota is intact.
Other models on the account keep working, and requests sent after the deadline succeed. Production saw it twice over
WebSocket, refused within 50–78 ms, before `response.created`.

codex-lb did not recognize the code. The turn reached the client as a 429, and the Codex client ended the turn with
"exceeded retry limit". CLIProxyAPI 9a35fa12 treats the code as transient capacity for that model and fails over to
another credential.

## What Changes

- `turn_rate_limit_exceeded` is a model admission limit. The shared model-capacity predicate recognizes it by code, so
  every pre-output retry path treats it as capacity.
- A pre-created direct WebSocket replay excludes the refusing account, as accepted replays already do, unless an owner pin
  or a possible hard sticky owner requires that account. Reconnecting to the same account would hit the same deadline.
- Accepted replays and pre-created classification report the code itself rather than `server_is_overloaded`. It is a
  transparent replay code, so owner-anchored turns follow the same owner-rejection rules as overload.
- The HTTP bridge replays it without the selected-model capacity wait, which exists for model-wide capacity.
- Account health records nothing for it, including the HTTP 429 burst backoff. The account's other models are unaffected.
- When no other account can take the turn, the upstream frame reaches the client unchanged, including its `Retry-After`,
  which the Codex client honors.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: adds the model admission limit requirement.

## Impact

- `app/modules/proxy/helpers.py`, `service.py`, the WebSocket helpers and mixin, the accepted-replay and HTTP bridge event
  handling, the streaming helpers and the retry loop.
- No setting, schema or dashboard change. There is no per-model cooldown: a later fresh selection may still pick the
  refusing account, which costs one early refusal before the same account move.
