# Tasks

## 1. Implementation

- [x] 1.1 Add the shared bundle projection (`app/core/openai/additional_tools.py`).
- [x] 1.2 Declare merged tools, skip bundle items and resolve the reserved namespace in `claude/protocol.py`.
- [x] 1.3 Merge bundles in model-source Responses forwarding; keep them in Claude's source compaction turn.

## 2. Verification

- [x] 2.1 Projection tests: precedence, namespace merge, hosted tools, reserved call namespace, unchanged requests.
- [x] 2.2 Claude protocol tests: merged declarations, Lite-era call, unchanged requests, malformed item.
- [x] 2.3 Forwarding and source compaction tests.
