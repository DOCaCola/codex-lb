## 1. Deadlines

- [x] 1.1 Give Antigravity requests a 180 s response-header deadline.
- [x] 1.2 Give Antigravity requests an 80 s first-event deadline.
- [x] 1.3 Report first-event timeouts on Antigravity and Claude as `model_source_timeout` with the applied deadline.

## 2. Verification

- [x] 2.1 Integration tests: the Antigravity path arms its deadlines, and a silent first event on Antigravity and
  Claude reports `model_source_timeout`.
- [x] 2.2 Ruff, type checks and the Antigravity, Claude and model-source suites pass; strict OpenSpec validation
  passes.
