## Why
On the OAuth path the adapter moves the client's instructions out of `system` into a conversation `system` turn after the first user turn. Translated cache placement still marks only `system` and the last two user turns. The relocated instructions and a developer turn after the last user turn therefore sit behind no breakpoint. On the first request of every new Claude thread or side chat, about 15.7K tokens are neither read from nor written to the cache, and the second request pays to write them.

CLIProxyAPI, which our relocation follows, has always put a breakpoint on each relocated system turn. Since its `f0034ca6` commit it also gives a request-ending system turn the rolling breakpoint, as Claude Code itself does.

## What Changes
- The OAuth projection reports which message holds the relocated instructions.
- Translated cache placement marks that turn's last block.
- A content-bearing system turn that ends the request becomes the newest of the two rolling message breakpoints.
- The total stays at four or fewer: `system`, the instructions, and two rolling message breakpoints.

## Capabilities
### Modified Capabilities
- `claude-accounts`: translated cache boundaries cover relocated instructions and a request-ending system turn.

## Impact
Changes only translated OAuth requests to Claude. Native Claude Code traffic, its cache markers and OpenAI models are unchanged. There is no schema or setting change.
