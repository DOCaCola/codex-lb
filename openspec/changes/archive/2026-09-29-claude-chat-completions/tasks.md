# Tasks

- [x] Route Claude Chat through the existing Responses dispatcher with one reservation owner.
- [x] Translate supported Chat controls, reject unsupported controls, and preserve tool roundtrip.
- [x] Project streaming and non-streaming Claude Responses into Chat with honest terminal semantics and usage.
- [x] Add public-route and converter regressions for success, failures, limits, tools and ownership.
- [x] Sync normative specs, context and user docs; validate and run focused tests/lint.
- [x] Restore genuine active tool reasoning from uniquely matched scoped replay; keep plaintext display-only.
- [x] Validate thinking display and inert controls; request summarized thinking where supported.
- [x] Cascade direct Chat stream closure and cover it with a regression.
- [x] Preserve caller-visible reasoning and reconstruct unsupported Chat tool cycles as paired ordinary conversation without fake signatures or lost content.
- [x] Attempt completed tool replay retention before downstream completion; cover JSON/SSE, restart/expiry, parallel, multimodal and later-turn behavior.
- [x] Synchronize main specs/context/docs and rerun focused/broader checks under the revised replay policy.
