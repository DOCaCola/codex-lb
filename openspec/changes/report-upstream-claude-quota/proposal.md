# Report upstream Claude quota exhaustion to Responses clients

## Why
Chat 01a105aa-8898-7222-89c5-3d31191961fb received an upstream Claude
429 after completing tool work. Codex scheduled a 7920.998-second retry sleep
and retained an in-progress turn. Local quota admission already emits the
Responses usage_limit_reached type, but the upstream refusal path does not.

## What Changes
- Translate positively identified upstream Claude quota-window refusals into
  Responses usage-limit errors, including attributable reset metadata.
- Reuse the existing scoped refusal classifier; preserve transient throttling,
  native Anthropic errors, retry headers, and authorized failover.
- Cover the externally failing HTTP and WebSocket surfaces.

## Impact
Claude-to-Responses error translation. No settings or storage migration.
