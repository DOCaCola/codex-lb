## Why
Native Claude Code Message Threads retain history and tools at Anthropic. A
continuation carries only `thread.previous_message_id` and new input. Current
soft affinity can rebind it to an account that does not own that retained state.
CLIProxyAPI issues #6338/#6346 and open PRs #6345/#6347 document this protocol and
client full-history replay after `thread_not_found`.

## What Changes
- Retain native thread response message ownership in scoped resource provenance.
- Require the original account for thread continuation, independent of soft
  session affinity; return a replayable missing-thread error for unknown state.
- Normalize narrowly identified upstream missing-thread 404s without account
  cooldown or cross-account replay.
- Preserve native body/tool/cache shapes and qualify recovery with Claude Code.

## Capabilities
### Modified Capabilities
- `claude-accounts`: native Message Threads ownership and recovery.

## Impact
Uses the existing resource provenance table; no new database migration.
