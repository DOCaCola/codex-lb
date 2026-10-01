## Why
On 2026-10-01 at 19:44Z (request `resp_msg_011Cfc6CncHZQj86xFu4kHog` and four retries) Claude Opus called a tool without arguments. Claude streams such a call as one `input_json_delta` with `partial_json: ""`. The adapter accumulated the empty fragment and parsed it at `content_block_stop`; `json.loads("")` failed and the response ended with `Claude returned invalid tool JSON`. Each retry chose the same call, so the conversation stalled. A live probe with a no-argument tool and `tool_choice: required` reproduces it.

The Anthropic SDK keeps the `input` from `content_block_start` when no argument JSON was streamed. OpenCodex treats an empty buffer as valid, and CLIProxyAPI uses `{}` for a completed call with empty arguments.

## What Changes
- Empty `input_json_delta` fragments SHALL carry no input. They SHALL not be buffered or forwarded as client argument deltas.
- A tool block without streamed argument JSON SHALL keep the `input` declared by `content_block_start`, and pass the same decoding and validation as a non-streamed block.
- Non-empty malformed argument JSON SHALL still fail.

## Capabilities
### New Capabilities
### Modified Capabilities
- `claude-accounts`: streamed tool calls without arguments.

## Impact
The Claude Responses stream projection and its tests. No migration or settings.
