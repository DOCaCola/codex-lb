# Conversation Cache Trace

## Why

Cache lapses were found by hand-written SQL against `request_logs`: which request of a conversation lost its cached
prefix, and why. Conversation Details only shows per-model totals, so a single expensive re-read is invisible.
Agent LB added a per-session trace for this (`eb929e74`, `ae1b4155`, `30ac3cd1`, `3b826831`): one row per request
with its cache-read share and an explanation for large uncached prompts. Every field it needs already exists in
`request_logs`.

## What Changes

- `GET /api/request-logs/conversation-trace?conversationId=&limit=&offset=` returns the conversation's eligible
  requests newest first, paginated, with prompt size, cache reads and writes, output, latency, status and a cache
  event. It requires conversation read permission and exposes no account identity.
- A request whose uncached prompt exceeds 20K tokens is classified by its first matching cause: `first`,
  `compaction`, `model_switch`, `account_switch`, `idle_expiry`, `bust`, `growth` or `miss`, following Agent
  LB's `cache_kind`. The predecessor of a page's oldest row is loaded so classification is page-independent.
- Conversation Details shows the trace as a timeline below the model table: elapsed-time bar coloured by cache-read
  band (≥80%, ≥30%, below), event tag with an explanation, error code for failures, and "load more".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-architecture`: adds "Conversation request trace".

## Impact

- `app/modules/request_logs/` (`trace.py`, repository, service, schemas, API).
- `frontend/src/features/dashboard/` (trace schema, API, hook, component, Conversation Details dialog), locales and
  mocks.
- No schema change. Subagent and side requests share their parent's conversation ID, so their divergent prompts
  appear as busts or misses in the parent's trace.
