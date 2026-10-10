## Why
For models with mid-conversation system support, OAuth instruction relocation moves the caller's system prompt into a `system` turn directly after the first ordinary user turn. Anthropic accepts a content-bearing system turn only before an assistant turn or at the end of `messages`. A non-native client request with several leading user turns, or with an effort directive (`{"role":"system","content":[],"output_config":{...}}`) between user turns, therefore had the system turn placed before a user turn and was rejected with a 400. Such requests appear right after a client compacts its conversation: the summary, an effort directive and the new user message, with no assistant turn yet. CLIProxyAPI fixed the same failure (`2d8ec73b`, issue #6477).

## What Changes
The relocated system turn is inserted after the leading run that starts with the first ordinary user turn. User turns and effort directives continue the run; any other turn ends it. The position stays stable as the conversation grows, so the cached prefix is unchanged, and no existing message is rewritten. Codex-translated requests are unaffected, because their translator merges consecutive user turns.

## Capabilities
### Modified Capabilities
- `claude-accounts`: relocated OAuth instructions follow the leading user run.

## Impact
Claude OAuth request projection and its tests. Native Claude Code requests are forwarded without relocation and are not affected.
