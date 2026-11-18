## Why

Claude Fable 5.1 and 5.2 reject `tool_choice` `any` and `tool` with HTTP 400,
as Opus and Sonnet 5.5 do; Fable 5 accepts them. CLIProxyAPI PR #7623 verified
this against the live API on 2026-11-17 and extended its tool-choice downgrade
to these two models. We serve both, but our downgrade covered only the 5.5
models, so forced tool use on Fable 5.1 or 5.2 would fail upstream.

## What Changes

- Fable 5.1 and 5.2, dated snapshots included, join the models whose forced tool
  choice is sent as `auto`, with the same `tool_choice_auto` transformation,
  and whose Responses translation accepts forced tool choice with thinking.
- Fable 5 and other models are unchanged.

## Impact

- `app/modules/claude/capabilities.py`.
- Tests: `tests/unit/test_claude_protocol.py`.
