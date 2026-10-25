# Advertise codex-lb Capabilities to Desktop Integrations

## Why

Codex desktop enables some client features only for threads on the built-in `openai` provider. Composer
predictions are one example. Threads served through codex-lb use a custom provider, so the desktop rejects
them as `unsupported_provider` before any request is sent, although codex-lb serves the resulting requests.

A CodexDC tweak can lift that restriction, but only for providers it can confirm are codex-lb. Matching on
URLs or provider names would be guesswork. codex-lb therefore needs to identify itself and list the client
features it serves, behind the same authentication as the rest of the proxy.

## What Changes

- `GET <base_url>/codex-lb/capabilities` returns a capability document under both `/backend-api/codex` and
  `/v1`, the two base URLs Codex providers use.
- The first capability is `composer_predictions`. Prediction forks are ordinary Responses turns that inherit
  the parent's model, history and prompt-cache key, so codex-lb serves them without further changes.

## Impact

- Specs: new `client-capability-discovery`.
- Code: `app/modules/proxy/api.py`, `app/modules/proxy/schemas.py`.
