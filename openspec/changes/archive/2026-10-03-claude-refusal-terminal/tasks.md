## 1. Terminal semantics

- [x] 1.1 Map `refusal` to incomplete `content_filter` for all translated Claude projections
- [x] 1.2 Log stop reason, status, block type counts and output tokens at each translated message stop

## 2. Verification

- [x] 2.1 Extend terminal-semantics unit tests (refusal with and without Chat reasoning, streamed and complete)
- [x] 2.2 Test the stop log contains counts only
- [x] 2.3 Run Claude protocol/Chat suites, ruff and ty

## 3. Documentation

- [x] 3.1 Update the claude-accounts context notes
