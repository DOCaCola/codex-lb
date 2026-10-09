## 1. Implementation
- [x] 1.1 Derive standalone search identity from `x-codex-turn-metadata`, with the body `id` as process-session fallback
- [x] 1.2 Route searches by the conversation's thread-locality key, else process-session affinity
- [x] 1.3 Record the metadata thread as conversation, the body model, and the client IP outside realtime calls

## 2. Verification
- [x] 2.1 Unit tests for identity precedence, invalid metadata, thread-key parity with Responses turns, process-session fallback and disabled affinity
- [x] 2.2 Integration tests for sibling-thread search routing, log attribution and body-`id` fallback
