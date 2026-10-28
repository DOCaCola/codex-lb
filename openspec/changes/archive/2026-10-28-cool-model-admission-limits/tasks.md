# Tasks

- [x] 1.1 Add the per-model admission cooldown to runtime state with default, cap and no-shortening bounds.
- [x] 1.2 Apply it in fresh and sticky selection: skip fresh, release soft owners request-locally, keep hard owners.
- [x] 1.3 Record it on the direct WebSocket, HTTP bridge and HTTP streaming surfaces at first recognition.
- [x] 1.4 Surface anchored turns that cannot move as promptly retryable `turn_rate_limit_exceeded`.
- [x] 1.5 Stop classifying model admission limits as HTTP 429 bursts; remove the WebSocket admission exclusion.
- [x] 1.6 Tests: bounds, model scoping, selection outcomes, frame `Retry-After`, anchored retry, HTTP no-burst.
- [x] 1.7 `openspec validate --strict`.
