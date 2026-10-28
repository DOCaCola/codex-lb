# Unforce Tool Choice For Claude 5.5

## Why

Opus 5.5 and Sonnet 5.5 reject forced tool use. A request with `tool_choice` `any` or `tool` fails with HTTP 400;
`auto` and `none` are accepted. A Codex turn with `tool_choice: "required"` or a named function, and any native client
that forces a tool, therefore fails outright on these models. On the translated path the gateway also rejected forced
tool choice combined with thinking before anything was sent.

CLIProxyAPI 1d45a5f3 (issue #7000) downgrades forced tool use to `auto` for these two models on every direct Claude
request, including native passthrough and token counting, keeps `disable_parallel_tool_use`, and runs before thinking
preparation so thinking and signed history stay intact. opencodex PR #5729 does the same. Both keep forced choices for
older models, which still honor them.

## What Changes

- Claude capabilities list the models that reject forced tool use: Opus 5.5 and Sonnet 5.5, dated snapshots included.
- Dispatch rewrites `tool_choice` `any`/`tool` to `auto` for those models on native, translated and token-counting
  requests, drops the tool name, keeps `disable_parallel_tool_use`, records the `tool_choice_auto` transformation and
  logs `claude_tool_choice_projection` with the model.
- The Responses translation no longer rejects forced tool choice combined with thinking for those models, since the
  forwarded request is `auto` with thinking. Other models keep the rejection.

The model may answer without calling the tool. That is the documented consequence of the upstream restriction and matches
the references.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: adds the forced tool choice requirement.

## Impact

- `app/modules/claude/capabilities.py`, `request.py`, `dispatch.py`, `protocol.py`.
- No setting, schema or dashboard change.
