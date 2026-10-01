# Verification: Claude interrupted turn recovery

Verified locally on 2026-10-01 against main at b195141d5. No archive, commit,
push, deployment, live history mutation or live generation was performed.
The unrelated claude-compaction-turn-boundary change was preserved.

## Completeness and correctness

All four tasks are complete; all three delta requirements are implemented and
synced into the corresponding main specs with stable context notes.

- History-preserving continuation: protocol unit tests cover Opus 5 and 5.5,
  text, signed thinking, reasoning-only history, input immutability, unchanged
  user/tool-result endings and missing-result rejection. Public Responses,
  backend Responses and Chat routes add exactly one wire user turn; native
  Messages preserves the original tail. Three authenticated empty-delta turns
  preserve signed blocks and prove the marker does not enter logical replay.
- Settled failures: unit tests verify cleanup, original error attribution,
  reservation release before error delivery, one log row, safe retry headers,
  no duplicate terminal, iterator closure and cancellation propagation,
  including cancellation during failed settlement. HTTP streaming routes emit
  structured errors after partial text; nonstreaming routes retain HTTP 502.
  Failed responses do not seed replay. Both public WebSocket routes recover
  on the same socket using assistant-tail full history after a projection error.
- Undeclared tools: strict rejection remains active. Safe, control-character,
  oversized and unpaired-surrogate names have bounded structural diagnostics
  without arguments or call IDs. Unknown tools never receive guessed aliases.

## Test results

Final affected-suite run: **355 passed**, one existing Starlette deprecation
warning. Command:

```sh
.venv/bin/pytest -q tests/unit/test_claude_protocol.py tests/unit/test_source_dispatch.py tests/integration/test_claude_inference.py tests/integration/test_claude_tool_schema.py --tb=short
```

The broader Claude/source regression run passed **1,409 tests** and exposed two
tests expecting escaped post-start exceptions. Both now assert the structured
error contract and pass in the final affected run. Its scope included all
tests/unit/test_claude*.py, source_dispatch, source_websocket,
model_sources_forwarding, all tests/integration/test_claude*.py,
model_source_dispatch, model_source_forwarding_deadlines and model_source_routing.
The broad run was not repeated after those expectation updates; the final
affected run also includes the additional cancellation/logging regressions.

## Static and spec checks

- Ruff lint and format checks pass for all eight changed Python files.
- Targeted ty checks pass for all four changed production files. Existing
  diagnostics in the inference test file occur on unchanged code; no new
  diagnostics remain in the added tests.
- Proxy timing-seam and cancellation-safety checks pass.
- git diff --check passes.
- Strict change validation passes; strict main-spec validation: **75 passed**.
  Since main specs are already synced, later archival must skip reapplying the
  ADDED deltas. The change remains active pending user authorization to archive.

Repository-wide checks are not green: ty reports 566 diagnostics, while the
architecture guard reports service.py 2603/2600 lines, load_balancer.py
3038/3021 and http_bridge/mixin.py 2472/2436. The architecture counts match HEAD;
none of those modules is changed here. These unrelated gates were not relaxed.

## Coherence and qualification limits

The solution uses the existing Claude projection and shared settlement owner,
not a client fork or a second cleanup/retry path. Cancellation deferred during
settlement propagates after the original outcome is recorded, rather than
being converted into an error for a departed client. Native Messages and Chat
retain their own error serializers.

No critical implementation issues remain within this change. Local tests prove
wire projection, structured error delivery, resource cleanup and same-socket
recovery. They do not establish live Anthropic acceptance or identify the actual
undeclared tool behind the production interruption, whose name was not captured
in the original logs. That tool remains an explicit failure with improved
diagnostics rather than speculative remapping.
