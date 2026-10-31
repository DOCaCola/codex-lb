## Why

Two Codex Desktop chats on Claude Opus 5.5 stopped with HTTP 400 "Tool results are
required before the next user message" and could not continue. Codex records input
that arrives while a tool runs, such as the goal-paused notice, where it arrived:
between the running call and its result. The Responses API accepts that order;
Claude requires a call's results to open the next user turn. The translator
rejected the history before dispatch, and every retry replayed the same order.

CLIProxyAPI, sub2api and OmniRoute repair the same shape by moving the results
ahead of the other content in that user turn.

## What Changes

- User input that arrives while tool calls are open is held and placed after the
  step's last result, in the same user turn and in its original order.
- The Antigravity translator places held input in the user turn after the step's
  function responses.
- A model step taken while held input still waits on results, and calls left
  without results at the end of the input, still fail before dispatch. Both
  errors point at the first open call's input item.

## Impact

- Backend: Claude and Antigravity Responses projection.
- No change to native Messages, Chat Completions replay or retained history.
