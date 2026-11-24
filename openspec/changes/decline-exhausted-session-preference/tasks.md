## 1. Implementation

- [x] 1.1 Decline an exhausted session seed preference for a new thread row when a non-exhausted sibling is the pool's best candidate

## 2. Verification

- [x] 2.1 Regression tests: exhausted preference moves to a sibling with quota left (fails without the fix); kept when the whole pool is exhausted; kept above threshold but below exhaustion
- [x] 2.2 Unit suite, ruff, ty and strict OpenSpec validation
- [ ] 2.3 Archive after deployment
