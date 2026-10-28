# Bound Native Egress Queues By Memory, Not Event Count

## Why

Since 2026-10-26, OpenAI has held back the complete answer on one production account and released it in a single burst. For
example, 6,632 output tokens arrived within 1.3 s after 104 s of reasoning. Such a burst is thousands of small delta frames
that total a few MiB. The native WebSocket message queue also capped its length at 4096 messages, so it dropped the turn as
`local_websocket_backpressure` about 0.4 s after the first visible token. This happened 34 times, and the Codex client then
retried the full turn, including its reasoning, up to 12 times per conversation.

The item cap protects nothing that the 32 MiB byte budget does not already protect. Upstream issue Soju06/codex-lb#2594
reports the same failure mode. Its open fix (#2635) only raises the cap to the 4096/32 MiB limits this fork already uses.

## What Changes

- Both native queues (the helper-reader per-request event queue and the per-WebSocket message queue) drop the item-count cap.
- Each payload-bearing item is charged its payload bytes plus a fixed 1 KiB per-item overhead against the existing 32 MiB
  budget. Many tiny items and a few large ones are therefore bounded by one memory measure.
- Payload-free control and terminal items are still always admitted and are never charged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `outbound-http-clients`: both native queue bounds become memory budgets that include per-item overhead.

## Impact

- `app/core/clients/native_egress.py`, native egress unit and integration tests, and `responses-api-compat/ops.md`.
- No settings, schema, dependency or routing change. A truly stalled consumer still fails with `consumer_backpressure`.
