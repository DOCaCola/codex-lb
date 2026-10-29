## Why

Operators want Google Antigravity subscriptions (Google AI Pro/Ultra and the free tier) as a third subscription provider next to Codex and Claude. Antigravity serves Gemini 3.8 Flash, Gemini 4 Argon and Claude-on-Vertex models over a private Cloud Code endpoint that only accepts its own client identity, so it needs native OAuth accounts, a faithful CLI wire image, per-family quota and a dedicated protocol adapter rather than an OpenAI-compatible source.

## What Changes

- Add Antigravity accounts: Google OAuth with PKCE through the native CLI's remote paste flow, credential import (agy, OmniRoute and CLIProxyAPI shapes), project discovery and onboarding, tier and credit display, reconnect by Google subject. New accounts start paused because the provider carries account risk.
- Follow the native CLI identity: verified `antigravity/cli/<version>` User-Agent including the build changelist, from the public update manifest with SHA-512-verified archive extraction, a seeded verified record, operator pin and per-request snapshots.
- Per-account catalog discovery (`fetchAvailableModels`) collapsed into effort families; per-family 5-hour and weekly quota from `retrieveUserQuotaSummary` with plan-weighted pace.
- Serve Codex Responses (HTTP, SSE and WebSocket) and the existing translated Messages/Chat front-ends through a Gemini `streamGenerateContent` adapter: native envelope, labels and per-account session ID, Google tool schema and name compilation, freeform/custom tools, signed thought replay carried in encrypted reasoning items, finish-reason and usage mapping.
- Error taxonomy, bounded retries and account failover following the design's decision table; bans, verification holds and reauth are durable account states.
- Dashboard: grouped add-account option, account list and detail cards with per-family quota bars, trends and the dashboard provider toggle.

## Capabilities

### New Capabilities
- `antigravity-accounts`: Account lifecycle, client identity, catalog, quota, routing, protocol adaptation and error handling for Google Antigravity.

### Modified Capabilities
- `openrouter-accounts`: The grouped add-account chooser gains an Antigravity group after Claude.

## Impact

New `app/modules/antigravity` module, five tables and one migration, proxy source dispatch and WebSocket routing, background scheduler, dashboard API and Accounts/Dashboard UI. Codex, Claude and OpenRouter behaviour is unchanged. No live Google requests are made by tests; contract tests use the captured CLI 1.4.10 wire image.
