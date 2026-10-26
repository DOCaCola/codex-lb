# Forward Cyber Policy Refusals and Stamp Per-Account Access Programs

## Why

Upstream now refuses flagged work with the error code `cyber_policy`. codex-lb recognized security-work refusals
only by the retired code `security_work_authorization_required` or by three phrases of the old message, so the
existing reroute to security-work-authorized accounts never fires for current refusals.

When no authorized account exists, HTTP streaming and compaction then re-send the flagged request to ordinary
accounts. The content is what was flagged, so every account refuses it again; the retries only add load and
delay. The WebSocket path forwards the refusal but replaces its code, so the client loses `cyber_policy` and the
notice Codex shows for it.

Codex sends `access_programs.cyber` only when its provider id is literally `openai`, which a codex-lb provider
never is. The program a request may use also depends on the upstream account that serves it: each account's model
catalog advertises its own `available_access_programs`. A program chosen by the client for one account fails on an
account without that entitlement.

## What Changes

- Security-work refusals are recognized by exact error code: `cyber_policy` or `security_work_authorization_required`.
  Message matching is removed.
- The original refusal keeps its upstream code on every transport and in request logs.
- When a reroute to an authorized account finds none, codex-lb forwards the original refusal at once over HTTP
  streaming and compaction, as WebSocket and the HTTP bridge already do. It no longer re-sends the request to
  ordinary accounts.
- codex-lb owns `access_programs` on native requests. For each selected account it sends the program a stock Codex
  client would send for that account's catalog entry of the model:
  - a Daybreak program (`daybreak_blue` before `daybreak_red`) when the account is marked security-work-authorized,
    which stands in for the client's Daybreak toggle;
  - otherwise `standard` when advertised;
  - otherwise no field.
  The program is re-derived whenever a request moves to another account, so the field never constrains failover or
  replay.
- The model registry records, per model, which accounts advertise each cyber program, with the same stale-account
  carry-over as service tiers. The persisted snapshot schema version is bumped.

## Impact

- Specs: modified `responses-api-compat`.
- Code: `app/modules/proxy/service.py`, `app/modules/proxy/capability_routing.py`, the streaming, compaction,
  WebSocket and HTTP-bridge proxy paths, `app/core/clients/proxy.py`, `app/core/openai/model_registry.py`,
  `app/core/openai/model_registry_store.py`, `app/modules/proxy/replay_safety.py`.
