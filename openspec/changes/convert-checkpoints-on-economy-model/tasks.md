# Tasks

## 1. Implementation

- [x] 1.1 Choose the conversion model in `CheckpointHandoff`; pass it to the generator and log it.
- [x] 1.2 Build the native handoff request with the chosen model in `proxy/api.py`.

## 2. Verification

- [x] 2.1 Unit tests: GPT-6 and gpt-5.6 mapping, other models, catalog absence or suppression, key restriction,
  summary attribution.
- [x] 2.2 Integration test: the native request and its request log use the conversion model.
