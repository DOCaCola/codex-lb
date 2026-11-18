## Why

From GPT-6.2 on, OpenAI appends top-level `instructions` after the input and never caches them. OpenAI's prompt-caching guide names a leading `developer` message as the cacheable placement. Current Codex already sends its base prompt that way for every model and provider, which is why native 6.2 traffic caches at about 97%. opencode measured the same effect on compaction requests (#64544), and sub2api #8930 reports it as well.

Three of our paths still place stable system text in top-level `instructions`:

- the Claude Code → OpenAI translator puts the system prompt there;
- Chat Completions and `/v1/responses` `messages` merge `system`/`developer` messages into it;
- Responses input normalization lifts `system` input messages into it (#950), because the Codex upstream rejects the `system` role in `input`.

On GPT-6.2 these prompts are paid for in full on every turn. CLIProxyAPI handles all three paths the same way: `instructions` stays empty, and system text becomes `developer` input at its original position.

## What Changes

- Responses and compact normalization rewrite `system` input messages to `developer` in place, without merging them into `instructions`.
- Chat Completions and `/v1/responses` `messages` map `system`/`developer` messages to `developer` input in place. A client's own `instructions` pass through unchanged. The JSON-mode special case (#731) is no longer needed, because every instruction message now stays in context.
- The Claude Chat replay history, which replaces the forwarded input for Claude sources, keeps those `developer` messages too. It used to skip them because they lived in `instructions`.
- The Claude Code translator sends system blocks as one leading `developer` message, one text part per block. Mid-conversation system messages use the same shape. The sessionless prompt-cache key keeps the same material.

## Impact

- Specs: `responses-api-compat`, `chat-completions-compat`, `messages-api-compat`.
- Code: `app/core/openai/requests.py`, `app/core/openai/message_coercion.py`, `app/core/openai/chat_requests.py`, `app/core/messages/translate.py`, `app/modules/claude/chat_replay.py`, and their tests and golden corpus.
- Each conversation on these paths takes one cache miss after deploy, because its prefix changes.
- Downstream adapters (Claude, Antigravity) already treat leading and mid-conversation `developer` messages as system text. OpenRouter accepts `developer` input.
- Client-supplied top-level `instructions` are untouched; they belong to the client.
