## 1. Implementation

- [x] 1.1 Queue sibling function calls while a tool block is open, and start them in announcement order once it closes
- [x] 1.2 Emit each function call as exactly one `tool_use` block, and drain queued calls at completion

## 2. Verification

- [x] 2.1 Regression tests: two overlapping calls finishing in order and in reverse, and a queued call unfinished at completion, each yield one sequential block per call (all fail without the fix)
- [x] 2.2 Unit suite, ruff, ty and strict OpenSpec validation
- [ ] 2.3 Archive after deployment
