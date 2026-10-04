# Proposal

## Why

The translated Claude projection gathered every Responses developer/system message, wherever it occurred, into the top-level system prompt. OAuth relocation then placed that prompt after the first user turn. Each new developer message during a conversation (sandbox or approval changes, model-switch notes, collaboration updates) therefore rewrote the relocated block near the start of the conversation and invalidated the cache from the first user turn onward. Anthropic also documents that editing an already-sent mid-conversation system message invalidates the thinking blocks of every later assistant turn on Opus 5.5.

## What Changes

- Developer/system messages before the first conversation message stay in the system prompt.
- Later ones keep their conversation position. For models with mid-conversation system turns they become `system` messages placed directly after the next user turn and before the following assistant turn or the end of the request, as Anthropic requires. For other models they close that user turn as a `<system-reminder>`.
- Requests containing system turns send the mid-conversation system beta, with or without relocated instructions.
- Signature recovery skips system turns when protecting the open tool turn.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: positional translated developer messages.

## Impact

Claude Responses projection, OAuth request projection and signature recovery. Active conversations whose history already contains later developer messages see one cache rewrite after deployment, because those messages move from the relocated block to their positions. Native Messages passthrough and the Chat path are unchanged. No migrations, settings or client changes.
