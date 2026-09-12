# Configurable Responses body budget

## Why

Image-heavy Codex histories can exceed the fixed 128 MiB ingress cap during the operation intended to compact them. Dedicated compact routes currently receive only the general 32 MiB cap. Increasing admission alone leaves replay and listener caps inconsistent.

## What Changes

- Add one validated restart-required instance resource setting, `CODEX_LB_RESPONSES_BODY_LIMIT_BYTES`, default 128 MiB, range 32–512 MiB.
- Share it across Responses/compact HTTP raw and decoded admission, default downstream WebSocket allowance, and expanded replay guards.
- Distinguish local ingress/replay refusals from upstream context verdicts; report safe byte measurements.
- Preserve unrelated route budgets, explicit WebSocket overrides, authorization, and request content.

## Impact

T1 instance resource setting: replicas can have different memory allocations. Raising the default globally is inappropriate because parsing and concurrent requests multiply memory consumption. No database migration or production change.
