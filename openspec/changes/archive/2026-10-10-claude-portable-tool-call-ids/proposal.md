## Why
Anthropic accepts `tool_use` IDs only when they match `^[a-zA-Z0-9_-]+$`. The Responses-to-Claude translator copied each Codex `call_id` verbatim into `tool_use.id` and `tool_result.tool_use_id`. A conversation that switches to Claude after another provider can carry call IDs outside that alphabet, such as `functions.shell:0`, and Anthropic rejects the whole request. CLIProxyAPI fixed the same failure (`e9c8769a`, issue #6478).

## What Changes
The translator writes each call ID in a deterministic wire form. IDs Anthropic accepts pass unchanged unless they carry the reserved prefix `cxlb_tid_v1_`; every other ID becomes that prefix plus its unpadded base64url encoding. The mapping is injective, so distinct call IDs never collide and no per-request ledger is needed. The call and its result use the same form. Pairing and validation still use the original call IDs. Claude's own IDs pass unchanged, so its replies need no reverse mapping, and native Messages passthrough is not affected.

## Capabilities
### Modified Capabilities
- `claude-accounts`: translated Claude tool IDs are portable.

## Impact
The Responses-to-Claude projection and its tests. There is no schema or client-visible change.
