## Why

Codex conversations moved to a cold account after a client reconnect even though their owner was healthy, below every threshold and not capped. Over 14 days, 47 of 397 continuations after a `client_disconnected` changed account, against 0.25% after a normal turn; 44 of them lost their prompt cache.

Two examples on 2026-11-20: chat `01a1f816` at 15:50 UTC and chat `019f9516` at 17:44 UTC. Both owners were weekly-only Pro accounts at 79% and 84% weekly usage, with thresholds at 95%. The reconnecting request found the owner's prompt-cache thread row, judged the owner over the sticky budget threshold and rewrote the row to an idle account at 1%.

The budget threshold read the pressure-adjusted usage. Every in-flight request or open stream adds the in-flight penalty (2.5 points by default), and a Codex WebSocket holds its stream lease for the whole connection, up to the stream budget plus grace (about two hours). The owners had served 16 and 33 WebSocket conversations in the preceding two hours; five to seven open streams were enough to lift them past 95%. A local reproduction against the real load balancer moved the conversation from five open streams on.

`fix-lease-pressure-credit-units` kept these gates on the adjusted values on the premise that pressure is now at most one lease plus the in-flight penalty. That premise holds per request but not per account: pressure grows with the number of connected chats. Pressure is a load-spreading signal; thresholds and exhaustion are quota decisions.

## What Changes

- Budget thresholds and usage exhaustion judge the usage upstream reported, without runtime in-flight pressure. This covers the sticky reallocation thresholds, the exhausted-owner release, and the budget-safe preference of fresh selection.
- In-flight pressure keeps its role in ranking candidates within the routing strategy.
- Status-gated priority usage (rate-limited or quota-exceeded accounts) keeps precedence as before.
- Routing settings copy and `docs/routing.md` no longer say that in-flight work makes thresholds trigger early.

## Impact

- Specs: `sticky-session-operations`, `frontend-architecture`.
- Code: `app/modules/proxy/_load_balancer/sticky_selection.py`; locale strings and the routing settings test.
- No settings, schema or client changes.
