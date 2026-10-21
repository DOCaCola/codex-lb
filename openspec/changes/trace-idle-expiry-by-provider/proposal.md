# Infer Trace Idle Expiry Only From Known Cache Lifetimes

## Why

The conversation trace labelled any Codex miss after a 5-minute gap as `idle_expiry`. That lifetime is Claude's.
OpenAI's prompt cache already lasted at least 30 minutes, and since 2026-10-20 signed-in Codex accounts keep their
cache indefinitely ("you don't have any penalty for coming back to an old conversation"). A cold Codex request after
a break is therefore unexplained by idle time, and the label hid exactly the case worth noticing. Other model sources
report no cache lifetime.

## What Changes

- `idle_expiry` applies only to Claude rows: 5 minutes, or 1 hour when the row wrote to the 1-hour tier.
- Codex and other model-source rows skip the idle rule, so a cold request after a gap is classified as `bust` or
  `miss`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-architecture`: "Conversation request trace" infers idle expiry only from known cache lifetimes.

## Impact

- `app/modules/request_logs/trace.py` and the trace sample in `service.py`. No schema or frontend change.
