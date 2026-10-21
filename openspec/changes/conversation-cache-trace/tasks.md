# Tasks

## 1. Backend

- [x] 1.1 Classify cache events per request (`trace.py`), adapted from Agent LB's `cache_kind`.
- [x] 1.2 Load a conversation page newest first, with its total and the predecessor of its oldest prompt row.
- [x] 1.3 Expose `GET /api/request-logs/conversation-trace` behind conversation read permission.

## 2. Frontend

- [x] 2.1 Schema, API client and paginated query hook.
- [x] 2.2 Timeline in Conversation Details with cache bands, event tags, failures and load more.
- [x] 2.3 English, Korean and Chinese labels.

## 3. Verification

- [x] 3.1 Unit tests for classification; integration tests for ordering, pagination, predecessor and permissions.
- [x] 3.2 Component tests for rows, bands, events and pagination.
- [x] 3.3 Full backend suite, frontend typecheck, lint, tests and build; `openspec validate --strict`.
