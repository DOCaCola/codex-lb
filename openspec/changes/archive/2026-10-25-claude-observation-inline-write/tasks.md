# Tasks

## 1. Observation write

- [x] 1.1 Remove the observation timeout; run the write to completion and deliver caller cancellation afterwards.

## 2. Verification

- [x] 2.1 Integration test: a write slower than the former bound still records the observation.
- [x] 2.2 Integration test: cancellation during the write lets it finish, then propagates.
- [x] 2.3 Full test suite, ruff, ty and `openspec validate --strict`.
