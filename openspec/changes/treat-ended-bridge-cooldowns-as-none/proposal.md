## Why

The HTTP bridge retry circuit maps the persisted cooldown onto the local clock as `now + remaining`, with `remaining` floored at zero. For a row with no cooldown, a zero cooldown or a cooldown that had already elapsed, this produced a deadline of "now". The admission gate treats any positive deadline that has passed as a cooldown that has just expired. It therefore armed the 600-second half-open probe lease, and every other retry on that hard-affinity conversation was refused for the lease ("HTTP responses session bridge is probing recovery…") although no cooldown was running. Each reload could manufacture the expiry again. Settlement adopting a surviving row and the post-write reconcile shared the same mapping.

This is upstream Soju06/codex-lb#2272. The maintainer confirmed this half by code reading and asked for it as a narrow change, separate from the probe-ownership work in PR #1962, which is still unresolved. The insciqq fork ships exactly that narrow change (v1.25.0-fork.3), and we follow it.

## What Changes

- A persisted cooldown that is missing, zero or elapsed maps to no local cooldown on load, post-write reconcile and settlement adoption.
- When the adopted row is the same episode and its cooldown has elapsed, the worker keeps its own local deadline. A real expiry it watched therefore still admits exactly one probe, and a consumed probe stays consumed. A replaced episode always takes the row's deadline and drops the ended episode's lease.
- Probe ownership and cleanup, the rest of PR #1962, are unchanged.

## Impact

- Spec: `responses-api-compat`.
- Code: `app/modules/proxy/_service/http_bridge/retry_circuit.py`.
- No settings, schema or client changes.
