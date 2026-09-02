# Tasks — restrict-public-text-backfill-to-messages

## 1. Contract

- [x] 1.1 Document message-only visible-text backfill and reasoning-item
      preservation in the `responses-api-compat` delta.

## 2. Implementation

- [x] 2.1 Gate synthetic output-text deltas on the normalized `message` item
      type.
- [x] 2.2 Add a unit regression for reasoning content in item-done and terminal
      response output.
- [x] 2.3 Add a model-source route regression for LiteLLM-style interleaved
      reasoning and visible-text events.

## 3. Validation

- [x] 3.1 Run focused unit and integration tests.
- [x] 3.2 Run Ruff checks on changed Python files.
- [x] 3.3 Run OpenSpec validation.
