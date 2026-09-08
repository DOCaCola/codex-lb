# HTTP fallback conversation replay

## Why
Codex sends incremental follow-ups after stateless HTTP fallback completions. An account-owner mapping cannot restore the omitted input and output, causing a missing-response retry on every turn.

## What Changes
- Retain complete HTTP-fallback input and completed output in a bounded, private, disk-backed continuation cache for one hour.
- Expand scoped incremental follow-ups before policy checks and upstream dispatch; preserve full resends without duplicate history.
- Treat HTTP response ownership as ephemeral in database lookups; request client replay when local state is unavailable.

## Impact
Conversation content, including embedded images and tool output, is temporarily stored under the server data directory. Normal upstream WebSocket continuity remains native. Cache loss is recoverable through the client's existing full-history retry.
