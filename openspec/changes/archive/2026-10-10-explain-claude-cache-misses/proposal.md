## Why
Codex side chats fork their parent conversation, but their first Claude request writes the whole prompt to the cache instead of reading the parent's cached prefix. One side chat on 2026-10-10 wrote 205,653 tokens at the 1-hour rate ($1.66) while the parent's turns before and after it were 99% cached. Every side chat since 2026-10-06 shows the same pattern. Because even the tools-plus-identity prefix missed, something in the forked request's prefix differs, but nothing records what, so the cause can only be guessed.

## What Changes
The Claude transport remembers the cacheable shape of each conversation's latest request: per-tool digests, the system digest, other top-level parameters and per-message digests, all with `cache_control` markers removed. When a request reads nothing from the cache but writes to it, and an earlier shape exists for the same conversation or for its parent session, the service logs one line naming which part differs: tools added, removed, changed or reordered, a changed system or parameter, and the first divergent message. Requests that hit the cache, and misses with no earlier shape, log nothing. Shapes are kept in a bounded in-memory LRU and contain digests only, never content.

## Capabilities
### Modified Capabilities
- `claude-accounts`: Claude cache misses are attributed to the changed prefix part.

## Impact
The Claude transport, the prepared Claude request (it carries the parent session ID), and a new diagnostics module with unit tests. There is no schema, routing or client-visible change.
