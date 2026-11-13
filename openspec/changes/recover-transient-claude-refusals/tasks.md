## 1. Implementation

- [x] 1.1 Classify Claude transient refusals (408, 409, ≥ 500, honouring `x-should-retry: false`) and share one retry sequence with pre-dispatch connection recovery
- [x] 1.2 Keep upstream text for non-JSON model-source error bodies on every forwarding path, including native Claude Messages
- [x] 1.3 Replace the OpenRouter-specific error body reader with the shared bounded reader

## 2. Verification

- [x] 2.1 Unit and integration tests, ruff, ty and strict OpenSpec validation
- [ ] 2.2 Archive after deployment
