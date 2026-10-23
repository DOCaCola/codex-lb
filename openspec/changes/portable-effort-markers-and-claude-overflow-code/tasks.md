# Tasks

## 1. Implementation

- [x] 1.1 Omit `configuration_update` from readable checkpoint projection.
- [x] 1.2 Add `code: context_length_exceeded` to translated Claude prompt overflow errors without an existing code.

## 2. Verification

- [x] 2.1 Checkpoint projection and retention tests with an effort marker in history.
- [x] 2.2 Claude overflow test for translated Responses and unchanged native Messages.
- [x] 2.3 Full test suite and `openspec validate --strict`.
