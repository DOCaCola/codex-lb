## 1. Implementation

- [x] 1.1 Classify ErrorInfo reason `TOS_VIOLATION` as a ban on any status
- [x] 1.2 Record each classified rejection in the transport where it is observed, before and after the stream opens and on later rounds
- [x] 1.3 Make recovery planning-only and drop its recording-only state
- [x] 1.4 Record account-level holds from gateway web search failures

## 2. Verification

- [x] 2.1 Regression tests: structured TOS reason with other wording and on HTTP 200; a suspension frame after visible output, collected and streamed, holds the account without walking the pool (fails without the fix); a search-call suspension is recorded
- [x] 2.2 Unit suite, Antigravity and model-source integration tests, ruff, ty and strict OpenSpec validation
- [ ] 2.3 Archive after deployment
