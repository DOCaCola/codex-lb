## Why

Messages streams cannot interleave content blocks: each block starts, receives its deltas and stops before the next one starts. When a GPT model on the Claude Code path makes parallel function calls whose stream events overlap, the projector switched blocks on every event. It started a block when the first call was announced and closed it to start the second. Then, when each call's arguments finished, it started that call again. Two parallel calls therefore reached Claude Code as four `tool_use` blocks, and some of them were duplicates with empty or missing input.

sub2api diagnosed the same defect in its Responses-to-Messages bridge (Wei-Shaw/sub2api#9071, open). Its fix serializes the calls: one tool block stays open, and sibling calls queue in announcement order with their arguments buffered.

## What Changes

- At most one `tool_use` block is open at a time. A function call announced while another tool block is open waits in a queue, in announcement order, and its argument deltas are buffered.
- When the open tool block finishes, the next queued call starts. If that call has already finished, its block is emitted whole with its final arguments. Otherwise its buffered arguments are flushed and the remaining deltas stream live.
- Every function call is emitted as exactly one `tool_use` block.
- At the end of the response, calls still queued are emitted with the arguments received so far.
- The completed item's arguments remain authoritative over deltas buffered before the tool name was known.
- Request translation already maps `disable_parallel_tool_use` to `parallel_tool_calls: false`, so no request change is needed.

## Impact

- Spec: `messages-api-compat`.
- Code: `app/core/messages/stream.py`.
- No settings, schema or client changes.
