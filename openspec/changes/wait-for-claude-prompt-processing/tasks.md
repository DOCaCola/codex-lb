## 1. Claude header deadline

- [x] 1.1 Give streamed Claude requests a 180 s response-header deadline.
- [x] 1.2 Report the applied deadline in model-source timeout messages.

## 2. Verification

- [x] 2.1 Integration tests: the Claude path arms the Claude deadline, and a silent source is cut at that deadline,
  not at 20 s.
- [x] 2.2 Ruff, type checks and the model-source and Claude test suites pass; strict OpenSpec validation passes.
