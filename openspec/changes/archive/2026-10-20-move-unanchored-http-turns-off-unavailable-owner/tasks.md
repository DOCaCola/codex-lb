# Tasks

## 1. Implementation

- [x] 1.1 Classify a durable row without a response anchor and a request without `previous_response_id` as complete
  input in `classify_account_neutral_replay_rejection`, projecting the whole input.

## 2. Verification

- [x] 2.1 Unanchored row with an unavailable owner moves to another account without affinity headers or the owner.
- [x] 2.2 Anchored row without input metadata still fails with `previous_response_owner_unavailable`.
- [x] 2.3 HTTP bridge, replay-rejection and proxy suites pass.
