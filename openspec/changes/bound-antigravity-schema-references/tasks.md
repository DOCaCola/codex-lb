## 1. Implementation

- [x] 1.1 Charge compiled nodes copied from `$ref` targets with their own UTF-8 size and one node
- [x] 1.2 Reject a tool schema copying more than 256 KiB, and a request copying more than 2 MiB or 50,000 nodes, as `unsupported_parameter`
- [x] 1.3 Share one budget across a request's tool declarations

## 2. Verification

- [x] 2.1 Regression tests: fan-out over the schema limit, reference-free schemas uncharged, charged copies under the limit, request byte and node limits across declarations, protocol-level shared budget
- [x] 2.2 Unit suite, Antigravity integration tests, ruff, ty and strict OpenSpec validation
- [ ] 2.3 Archive after deployment
