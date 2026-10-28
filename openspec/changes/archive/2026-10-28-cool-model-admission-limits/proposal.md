# Cool Model Admission Limits Per Model

## Why

`turn_rate_limit_exceeded` ("Codex is at capacity") refuses one model on one account until its `Retry-After`. The
proxy moved the refused turn, but only within that request: the next turn of the same conversation went straight back to
the refusing account, because soft sticky ownership and fresh selection knew nothing about the refusal. An anchored turn
that could not leave its owner surfaced as `upstream_unavailable` / "Previous response owner account is unavailable;
retry later", which hides the cause and makes Codex give up instead of resending the turn without the anchor.

The HTTP path also classified an HTTP 429 `turn_rate_limit_exceeded` as an upstream burst, engaging the account-wide
burst cooldown and a same-account sleep for a refusal that only concerns one model.

CLIProxyAPI 9a35fa12 records a per-model cooldown from the refusal's `Retry-After` and skips that model on that account
in selection until it expires; agent-lb uses a 15 second default when no `Retry-After` is given.

## What Changes

- The runtime keeps a per-model admission cooldown per account, recorded where each surface first recognizes the
  refusal: direct WebSocket, HTTP bridge and HTTP streaming. Duration is the refusal's `Retry-After`, 15 seconds without
  one, at most 600 seconds; a later refusal never shortens it. No account health is written.
- Selection for that model avoids cooling accounts: fresh selection skips them, soft sticky owners are released for
  the request with their mapping kept, hard owners stay pinned, and the pool is never emptied.
- An anchored turn that cannot leave the refusing owner fails with `turn_rate_limit_exceeded` and upstream's message,
  which Codex retries promptly without the anchor; the cooldown then moves the retried turn.
- When every candidate account is cooling, the upstream refusal and its `Retry-After` reach the client unchanged.
- A model admission limit no longer counts as an HTTP 429 burst. The admission-specific direct WebSocket exclusion is
  replaced by the cooldown.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: model admission limits cool the model per account.

## Impact

- `app/modules/proxy/_load_balancer/` (`overload_backoff.py`, `types.py`, `sticky_selection.py`,
  `unbound_selection.py`, `opportunistic_admission.py`), `load_balancer.py`, `helpers.py`.
- `app/modules/proxy/_service/` WebSocket, HTTP bridge and streaming surfaces.
- No setting, schema or dashboard change. The cooldown is in-process runtime state.
