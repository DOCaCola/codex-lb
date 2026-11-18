## 1. Implementation

- [x] 1.1 Fail closed in the full-resend predicate for anchors the connection did not complete
- [x] 1.2 Record whether a completed request's input covered its whole context; inherit it for injected session anchors
- [x] 1.3 Require that coverage before a stored prefix proves a full resend, for completions and empty prewarms
- [x] 1.4 Serialize a history replay like a client body with its input, so a history with a Lite tool bundle is a Lite body
- [x] 1.5 Update tests: Lite fresh replay, stale-anchor diagnostics, retained-history replay after a restated delta

## 2. Verification

- [x] 2.1 Full test suite, ruff, ty and strict OpenSpec validation
- [ ] 2.2 Archive after deployment
