## Why
Claude discovery advertises provider capacity directly as the normal client
working budget. Opus 5.5 therefore exposes 950k usable tokens, unlike current
Codex models' conservative default context and separately declared maximum.

## What Changes
- Default Claude client context to the lesser of 272000 and discovered capacity.
- Advertise the real maximum separately, with 95% usable context and 90% default
  compaction. Preserve discovery, output ceilings and existing output defaults.
- Derive policy at client catalog construction so existing accounts adopt it
  without rewriting their persisted capabilities or waiting for refresh.

## Capabilities
### Modified Capabilities
- `claude-accounts`: default context policy distinct from provider capabilities.

## Impact
Client model metadata only. No migration, manual token editors, upstream request
rewrites, compaction-history fix, deployment or production configuration change.
