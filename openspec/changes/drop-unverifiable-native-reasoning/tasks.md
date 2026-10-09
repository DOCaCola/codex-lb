# Tasks

## 1. Implementation

- [x] 1.1 `project_native_replay` omits authenticated Claude thinking and redacted thinking, and logs
  `thinking_omitted`/`search_projected` counts.
- [x] 1.2 `sanitize_native_reasoning_input` drops reasoning items without non-empty `encrypted_content`, clears
  plaintext `content` on kept items and logs `unverifiable_omitted`.

## 2. Verification

- [x] 2.1 Unit tests: Claude thinking omitted with tool pairs intact; summary-only, plaintext, unknown-content and
  empty-encryption reasoning omitted; native encrypted reasoning kept with plaintext cleared.
- [x] 2.2 HTTP stream, compaction and WebSocket tests: foreign reasoning never reaches the native upstream.
- [x] 2.3 ruff, ty, pytest, strict OpenSpec validation.
