## 1. Implementation

- [x] 1.1 Close the wrapped stream in every account-backed stream wrapper on exit
- [x] 1.2 Return the error-event generator directly from `_stream_proxy_errors_as_response_failed`

## 2. Verification

- [x] 2.1 Regression tests on the real wrapper chain: a mid-chain synthetic transport failure and an early close each release the lease-holding root; each prepend and fallback helper closes its root on early close (all fail without the fix)
- [x] 2.2 Unit and integration suites, ruff, ty and strict OpenSpec validation
- [x] 2.3 Archive after deployment
