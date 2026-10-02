# Tasks

## 1. Liveness policy

- [x] 1.1 Define the fixed upstream liveness bound (20 s ping interval, 30 s pong timeout) and its aiohttp heartbeat mapping.
- [x] 1.2 Apply it to the direct native, Python `websockets`, routed native, and routed aiohttp transports, independent of the downstream idle timeout.

## 2. Native helper

- [x] 2.1 Any inbound frame clears the pending pong deadline.

## 3. Dashboard copy

- [x] 3.1 Remove the upstream liveness clause from the idle timeout description.

## 4. Tests

- [x] 4.1 A connection that streams frames but never answers pings stays open while frames arrive, then trips once silent.
- [x] 4.2 A connection with no reply trips the liveness timeout.
- [x] 4.3 Direct and routed transports receive the fixed bound; aiohttp receives the heartbeat that preserves the pong bound.
