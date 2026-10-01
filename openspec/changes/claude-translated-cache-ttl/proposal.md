## Why
Translated Claude requests use 5-minute cache breakpoints. Agent turns often
pause longer than 5 minutes for tool work or review, so the prefix is written
again. Over the last 7 days, 41 of 42 turns after a 5–60 minute gap missed the
cache (about $32 at list price), versus 25 of 1,146 turns after shorter gaps.
No row has ever recorded a 1-hour cache write.

Claude Code 2.1.283 sends `{"type":"ephemeral","ttl":"1h"}` with beta
`extended-cache-ttl-2025-04-11`. CLIProxyAPI and OmniRoute upgrade
breakpoints to 1h on the Claude OAuth path. opencodex and sub2api default to
5m as a cost policy for API-key/pass-through use. This gateway presents as
Claude Code on OAuth, so it follows Claude Code.

## What Changes
- Gateway-owned breakpoints on translated requests use the 1-hour TTL.
- Translated requests send `extended-cache-ttl-2025-04-11`.
- Native Claude Code passthrough keeps its own markers and betas.

## Capabilities
### Modified Capabilities
- `claude-accounts`: translated cache boundaries use the 1-hour tier.

## Impact
1h writes cost 2× base input instead of 1.25×; per-turn incremental writes are
a few thousand tokens. No migration or client change.
