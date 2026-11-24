## 1. Implementation

- [x] 1.1 Judge budget thresholds and usage exhaustion on reported usage in sticky selection and the budget-safe preference
- [x] 1.2 Update routing settings copy (en, ko, zh-CN) and `docs/routing.md`

## 2. Verification

- [x] 2.1 Regression tests: busy prompt-cache owner below threshold keeps its conversation; fresh selection treats a busy under-budget account as budget-safe (both fail without the fix)
- [x] 2.2 Unit suite, frontend routing settings test, ruff, ty and strict OpenSpec validation
- [x] 2.3 Archive after deployment
