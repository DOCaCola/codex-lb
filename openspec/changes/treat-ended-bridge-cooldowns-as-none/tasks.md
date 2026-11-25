## 1. Implementation

- [x] 1.1 Map missing, zero and elapsed persisted cooldowns to no local cooldown on load, post-write reconcile and settlement adoption
- [x] 1.2 Keep the local deadline for an unchanged episode whose persisted cooldown has elapsed

## 2. Verification

- [x] 2.1 Regression tests: loading an absent or elapsed at-threshold row admits repeatedly without a probe lease (fails without the fix); a watched local expiry still admits exactly one probe
- [x] 2.2 Unit suite, bridge integration tests, ruff, ty and strict OpenSpec validation
- [ ] 2.3 Archive after deployment
