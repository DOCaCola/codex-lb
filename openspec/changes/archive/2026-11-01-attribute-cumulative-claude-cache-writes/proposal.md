## Why

Claude requests that sample in several server-side rounds (for example web search)
report a cumulative cache-write total in `message_delta` without restating its
5-minute/1-hour split. The merged usage kept the `message_start` split of the first
round, so the split no longer added up to the total and the API-equivalent cost
became unknown. Production showed 42 of 33,716 cache-writing Claude requests in 14
days without a cost, all Opus 5.5. sub2api #8412 documents the same protocol
behavior.

## What Changes

- A cumulative usage update that changes the cache-write total without a split
  attributes the whole total to the request's single cache lifetime, read from
  the cache markers of the body actually sent.
- With mixed or absent cache lifetimes the split becomes unknown instead of stale,
  so the cost stays explicitly unknown.
- Applies to translated Responses and native Messages streams.

## Impact

- Backend: `app/modules/claude/responses.py`, `native.py`, `request.py`, `transport.py`.
- Existing rows are not repriced.
