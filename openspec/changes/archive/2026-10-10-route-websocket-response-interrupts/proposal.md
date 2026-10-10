## Why
Codex stops a running GPT-6 turn by sending `response.interrupt` over the Responses WebSocket and waits for that response's terminal event. codex-lb forwarded the frame verbatim. An interrupt that crossed the response's terminal event reached upstream for a finished response, and upstream's error was attributed to the client's next turn. An interrupt sent before any upstream existed was rejected with a 400. A turn relayed over HTTP because of its frame size could not be interrupted at all. An interrupted response was also logged as an error and was not remembered as the anchor of the follow-up turn, although Codex continues from it with `previous_response_id`. CLIProxyAPI fixed the same behaviour (`d318bcc3`, issue #6483).

## What Changes
- A `response.interrupt` is delivered only to the in-flight response it names. A WebSocket turn receives the frame with the upstream response ID. An HTTP-relayed turn is cancelled locally and ends with `response.incomplete` (reason `interrupted`) carrying its completed output items. An interrupt naming no in-flight response is consumed.
- Upstream events naming a response that already reached its terminal event on the connection are dropped instead of being attributed to another pending request.
- An interrupted response is logged as `cancelled` with error code `interrupted`, and it anchors the follow-up turn like a completed response: its owner is remembered and the owner lookup accepts it.
- Request Logs expose interrupted rows with their own public status `interrupted`, with its own filter option and a localized non-error badge, like connection-limit reconnects.

## Capabilities
### Modified Capabilities
- `responses-api-compat`: Codex WebSocket response interrupts are routed to the in-flight response, and interrupted responses are cancellations that anchor the follow-up.
- `usage-error-metrics`: Interrupted cancellations are a distinct public Request Logs status.

## Impact
The WebSocket downstream loop and upstream event routing, the Responses transport's HTTP relay, request-log finalization, the owner lookup, the Request Logs status filter and the dashboard status badge, plus tests. There is no schema change, and account health is unchanged because an incomplete terminal was never penalized.
