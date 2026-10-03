## Implementation
- [x] Accept mid-stream refusal with open blocks in the translated projection, discarding the partial output.
- [x] Accept refusal with open blocks in native passthrough and classify incomplete terminals.
- [x] Map pause_turn and model_context_window_exceeded to max_output_tokens.
- [x] Name the failing condition in unfinished-stop errors and log stop diagnostics before failing.
- [x] Name the exception class in transport failures.
- [x] Test, lint, type-check and validate specs.

Verification: 1327 Claude, dispatch, forwarding and Chat-mapping tests passed; the
WebSocket roundtrip test passes serially and fails under parallel runs on the
unchanged baseline as well. Ruff, formatting, diff checks and strict change
validation passed; ty reports no new diagnostics. Not committed or deployed.
