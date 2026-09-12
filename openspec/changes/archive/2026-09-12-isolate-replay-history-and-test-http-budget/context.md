# Replay ownership and transport limits

The normalizer intentionally shares some nested JSON objects to avoid validating/copying the whole passthrough tree. Replay needs the original history, not an alias that subsequent preparation can mutate. Snapshot only input, after successful retained-history expansion and before normalization. A shallow dictionary/list copy does not isolate nested tool definitions. Validate the established depth budget before the recursive copy so deeply nested input remains a client validation error.

For example, normalizing an additional_tools definition can mutate an object reachable from raw input. The independently owned snapshot must retain the original definition when the HTTP response completes, even if the incoming array is later cleared. A previous_response_id that could not be expanded does not earn a complete-input snapshot.

The bridge has two different budgets: crossing the upstream WebSocket frame threshold chooses HTTP, while crossing the expanded Responses HTTP budget rejects the request. Synthetic interrupted outputs and installation metadata must be counted at the latter boundary. Historical images are not removed merely to fit the WebSocket frame.

The integration test keeps the real ResponsesTransport and mocks only network endpoints. An idle WebSocket may already exist when the bridge allocates its session; the invariant is that the oversized frame is dispatched only through same-account HTTP, then a small turn can use WebSocket. It is not a requirement to prohibit an idle socket.

Dump diagnostics remain covered independently by test_proxy_utils: product-path oversized-error capture, same-payload deduplication, orphan metadata repair, retention limits and write failures. HTTP-budget rejection tests no longer depend on the removed WebSocket-size rejection/dump coupling.

## Verification

- 1,879 tests passed across passthrough fields, replay store, transport, proxy utilities, HTTP bridge and direct WebSocket integration suites.
- The subsequent snapshot/depth/dump regression selection passed all 12 cases, including two additional deep-input tests at 300 and 5,000 levels.
- Final focused rerun of the original failure paths passed all five cases.
- Full ty check, scoped Ruff lint/format checks, and strict validation of all 65 canonical OpenSpec capabilities passed.
- No commit, push or production change performed.
