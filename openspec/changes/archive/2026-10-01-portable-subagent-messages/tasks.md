## Implementation
- [x] 1. Add the native collaboration projection and restoration helper.
- [x] 2. Project tools in `sanitize_native_responses_input`; restore in `stream_responses` and `ResponsesTransport`.
- [x] 3. Add the shared `agent_message` lowering and apply it where Claude and model-source Responses payloads are shaped.
## Verification
- [x] 4. Add regression tests; run the native, Claude, OpenRouter and model-source suites, ruff and ty.
- [x] 5. Probe the projected schema live and validate the change.
