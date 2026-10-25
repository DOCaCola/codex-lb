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
- Each capability names the models it applies to. The first is `composer_predictions`, limited to native
  subscription models. A prediction fork re-sends its parent's history plus a prediction prompt under the
  parent's prompt-cache key, which native models serve largely from cache. Routed sources (Claude,
  OpenRouter) are excluded until their prediction cost is measured.
- Request logs label prediction turns `composer_prediction`, from the `thread_source` in Codex turn
  metadata, so their cache ratio and cost can be measured. The label affects nothing but the log.

## Impact

- Specs: new `client-capability-discovery`; modified `provider-request-log-attribution`.
- Code: `app/modules/proxy/api.py`, `app/modules/proxy/schemas.py`, `app/core/openai/turn_metadata.py`,
  `app/core/usage/request_operation.py`, the WebSocket response-create path, and the dashboard operation label.
