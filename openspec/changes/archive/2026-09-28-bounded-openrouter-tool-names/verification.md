# Verification: bounded-openrouter-tool-names

## Completeness
Three of three tasks complete. One added requirement with four scenarios synced
to the main OpenRouter account spec; stable rationale synced to context.md.

## Correctness
- Unit tests cover deterministic bounded names, reserved aliases, distinct namespace
  identities sharing flattened spelling, declaration order, history-only calls,
  explicit/allowed tool choices, unchanged arguments and request immutability.
- Stream tests cover LF/CRLF/CR framing, one-byte UTF-8 chunking, item and terminal
  restoration, fragmented Chat names, ordinary names sharing an alias prefix,
  SSE metadata and early iterator closure.
- Public HTTP tests exercise both Responses aliases and Chat Completions, streaming
  and non-streaming, with a real local HTTP stub enforcing the name limit.
- WebSocket continuation tests use the reported document namespace/name, both
  custom/function tools, both route aliases, same connection and reconnect.
  They assert original client identity and stable upstream replay aliases.
- Echoed Responses tool declarations/selection restore original request values.

## Coherence
Mapping stays per request and is only projected for native OpenRouter sources.
Native OpenAI, Claude and generic compatible source behavior remains unchanged.
Existing source transport retains ownership of deadlines, usage and cleanup.
No request IDs, tool arguments or tool results are rewritten.
Source inspection informed the design; no third-party code was copied.

## Results
- Broad OpenRouter/model-source tests: 420 passed.
- Focused unit/public HTTP/WS tests after echo restoration: 59 passed.
- Affected-file lint, formatting and application type checks passed.
- Strict change validation and all 72 main specs passed.
- git diff --check passed.
- Existing Starlette/AnyIO deprecation warning only.

No critical issues or warnings from verification. No billable inference replay,
commit, push or deployment. These tests establish the name-mapping contract;
they do not establish that GLM accepts every other field in the production request.
Ready for archive confirmation.
