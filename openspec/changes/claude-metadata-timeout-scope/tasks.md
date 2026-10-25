# Tasks

## 1. Refresh

- [x] 1.1 Limit the metadata fetch timeout to the upstream request; verify the subscription identity afterwards.

## 2. Verification

- [x] 2.1 Integration test: a slow identity check outlasting the fetch timeout still records the subscription.
- [x] 2.2 Full test suite, ruff, ty and `openspec validate --strict`.
