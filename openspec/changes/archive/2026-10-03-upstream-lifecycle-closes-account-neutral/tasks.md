## 1. Classification

- [x] 1.1 Add a shared predicate for received upstream lifecycle close frames (`1000`, `1001`, `1012`)
- [x] 1.2 Skip the account penalty for those closes on direct WebSocket transport end
- [x] 1.3 Skip the account penalty for those closes in the HTTP bridge reader, replacing the narrower clean pre-response waiver

## 2. Verification

- [x] 2.1 Unit tests: direct WebSocket and HTTP bridge lifecycle closes do not penalize; `1011` still penalizes
- [x] 2.2 Run the affected proxy suites, ruff and ty

## 3. Documentation

- [x] 3.1 Update the responses-api-compat context notes
