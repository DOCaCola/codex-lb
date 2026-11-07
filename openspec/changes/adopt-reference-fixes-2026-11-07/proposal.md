# Adopt reference fixes from November 7

## Why

A review of recent reference changes found three defects that affect us:

- **Claude sign-in scope.** Since about November 6, claude.ai has rejected
  authorize URLs that omit `org:create_api_key` (CLIProxyAPI #7316, fix
  ea0b4712). Claude Code 2.1.285 requests that scope first, followed by
  `user:profile` and the claude.ai scopes. Our sign-in URL omitted it, so new
  enrollments and reauthorization would fail. Token refresh sends no scope, so
  existing accounts are unaffected.
- **Codex output-limit floor.** Since we began forwarding client output limits,
  a Claude Code one-token probe or any limit below 16 reaches the Codex
  backend, which rejects `max_output_tokens` below 16 (CLIProxyAPI bfac8586,
  9be48133; #7304, #7282).
- **Empty catalog discovery.** A successful but empty discovery reply replaced
  the served catalog, so every selected model became unavailable until the
  next good sync (OmniRoute 29f1b71ea). An empty reply is not evidence that
  every model went away.

## What Changes

- The Claude authorize URL requests exactly Claude Code's scope set:
  `org:create_api_key user:profile user:inference user:sessions:claude_code
  user:mcp_servers user:file_upload`.
- At the Codex backend boundary, a positive output limit below 16 is raised
  to 16. Model sources (OpenRouter, Claude, Antigravity) still receive the
  client's value.
- OpenRouter, Claude and Antigravity discovery that returns no models fails
  the sync and records a catalog error. The previous snapshot is kept, as for
  any other failed sync. Antigravity models that the plan gates off are still
  a real answer and still replace the catalog.

## Impact

Claude OAuth enrollment, Codex request shaping, and provider catalog
synchronization. Not verified against the live servers.
