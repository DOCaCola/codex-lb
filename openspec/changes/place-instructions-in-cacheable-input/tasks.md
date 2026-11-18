## 1. Implementation

- [x] 1.1 Rewrite `system` input messages to `developer` in place in Responses and compact normalization
- [x] 1.2 Map Chat and `/v1/responses` instruction messages to in-place `developer` input; remove the JSON-mode special case
- [x] 1.3 Send Claude Code system blocks as a leading `developer` message
- [x] 1.4 Keep Chat `system`/`developer` messages in the Claude Chat replay history, which replaces the forwarded input
- [x] 1.5 Update tests and the passthrough golden corpus; add Claude Chat system-message coverage

## 2. Verification

- [x] 2.1 Full test suite, ruff, ty and strict OpenSpec validation
- [ ] 2.2 Archive after deployment
