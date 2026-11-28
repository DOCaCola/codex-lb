## Why

Antigravity requests shared the Responses model-source deadlines: 20 s for response headers and 30 s for the first
event. Cloud Code can withhold its headers, or its first event, until it has processed the prompt, so a large uncached
prompt can outlast both, the same failure that blocked a 295k-token Claude compaction on 2026-11-28. A first-event
timeout was also reported as `invalid_upstream_response` ("Antigravity did not start an SSE response"), which hides
that a deadline ended the request and keeps it out of the timeout metric. The Claude transport reported its
first-frame timeout the same way.

OmniRoute, the reference with dedicated Antigravity handling, bounds the pre-response wait at 600 s and gives the
stream 80 s to produce its first event.

## What Changes

- Antigravity requests wait up to 180 s for response headers, the bound Claude already uses.
- Antigravity requests wait up to 80 s for the first event after headers, following OmniRoute.
- A first-event or first-frame deadline on Antigravity and Claude fails with `model_source_timeout` (HTTP 504),
  naming the deadline that applied, and counts toward the first-frame timeout metric. A stream that ends or goes idle
  before its first event remains `invalid_upstream_response`.

## Impact

- Specs: `antigravity-accounts`, `claude-accounts`.
- Code: `app/modules/antigravity/transport.py`, `app/modules/claude/transport.py`.
- Connection establishment, the stream idle cap and client cancellation are unchanged.
