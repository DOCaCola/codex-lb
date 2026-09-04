## Why

Current Codex clients advertise `gpt-6-astra`, but codex-lb's static bootstrap
catalog stops at GPT-5.6. Before the first successful live model refresh, the
model is therefore absent from both Codex-native and OpenAI-compatible model
discovery even when an account can serve it.

## What Changes

- Add `gpt-6-astra` to the static bootstrap catalog and websocket preference
  fallback.
- Mirror the installed Codex 0.153.1 catalog metadata that affects client behavior,
  including Astra's reasoning levels, context limits, unified-exec shell,
  tool-mode, multi-agent, Responses Lite, speed-tier, and Node REPL fields.
- Keep large account-specific `model_messages` out of the bundled entry and
  continue treating a successful live catalog refresh as authoritative.
- Use the current frontier plan set only as the pre-refresh routing floor;
  live per-account advertisements remain authoritative for actual routing.
- Add Astra to the existing static cost-accounting table with published
  Standard, Fast/priority, Flex, and long-context input, cached-input, and
  output rates, including suffixed model aliases.

## Impact

- No database migration or new configuration.
- Startup/offline model discovery includes `gpt-6-astra` with client-compatible
  metadata.
- API-key reservations, request logs, and aggregate reports no longer treat
  Astra usage as zero-cost.
- Cache-write and regional-processing accounting remain outside this change,
  consistent with the existing pricing model for other catalog entries.
