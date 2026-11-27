## 1. Implementation

- [x] 1.1 Classify with RetryInfo first and the HTTP `Retry-After` as fallback on 429 and overload answers, keeping an explicit 0
- [x] 1.2 Keep a bare `RESOURCE_EXHAUSTED` unexplained regardless of the header delay; replay it from the classified delay
- [x] 1.3 Wait out short overload delays in place; move once on longer ones
- [x] 1.4 Cool the model on the account for rate limit and overload delays of at least 3 seconds
- [x] 1.5 Pace rate-limited metadata from the classified delay, else the endpoint interval; remove the metadata client's own delay parsing

## 2. Verification

- [x] 2.1 Regression tests: header fallback, body precedence, explicit 0, HTTP date, bare 429 with a long header, 503 capacity delays, overload pacing, cooldown recording, capacity rejection end to end, metadata pacing (fail without the fix)
- [x] 2.2 Unit suite, Antigravity integration tests, ruff, ty and strict OpenSpec validation
- [x] 2.3 Archive after deployment
