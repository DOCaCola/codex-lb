## Why
Codex standalone web search (`POST /backend-api/codex/alpha/search`) sends none of the `session-id`, `thread-id` or `x-codex-turn-state` headers that control requests route on. Every search therefore entered account selection without affinity and landed on the highest-priority account (96 of 100 production searches on the Plus account since October 4, 2026), away from the account serving its conversation. Search log rows also had no conversation, model or client IP, so they could not be related to the conversation that issued them.

The search client carries the same identity its Responses turns send as headers, in the `x-codex-turn-metadata` JSON header (`session_id`, `thread_id`), and repeats the process session as the body `id`. CLIProxyAPI and sub2api already use the body `id` as the search routing seed.

## What Changes
- Derive standalone search identity from turn metadata, with the body `id` as the process-session fallback.
- Route a search through the same thread-locality key its conversation's Responses turns use; without a thread, use process-session affinity.
- Record the metadata thread as the search's conversation, the body model as its model, and the client IP for Codex control requests. Realtime calls keep redacting the client IP.
- Forward the search body unchanged.

## Capabilities
### Modified Capabilities
- `responses-api-compat`: standalone Codex web search routing and request-log attribution.

## Impact
Codex control-request routing and request logging. No schema change or deployment configuration. Historical search rows remain without conversation, model or client IP.
