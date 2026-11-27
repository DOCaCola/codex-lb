## 1. Implementation

- [x] 1.1 Record which Claude models produce account-bound thinking
- [x] 1.2 Convert completed thinking during compaction only when the selected model or, for account-bound models, account cannot read it

## 2. Verification

- [x] 2.1 Unit tests: account-bound thinking on another account converts; portable thinking on another account or identity generation stays signed; model switches still convert
- [x] 2.2 Unit suite, Claude integration tests, ruff, ty and strict OpenSpec validation
- [x] 2.3 Archive after deployment
