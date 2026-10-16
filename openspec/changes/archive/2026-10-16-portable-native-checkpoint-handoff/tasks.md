# Tasks

## 1. Implementation

- [x] 1.1 Remove `required_account_id` from the streaming retry path and `_collect_responses`; handoff generation
  uses ordinary selection.
- [x] 1.2 `CheckpointHandoff` rechecks only the API key identity and model access, for generation and cached summaries.
- [x] 1.3 Attribute handoff request logs to the destination turn's conversation via `request_log_conversation_id`.
- [x] 1.4 Classify `invalid_encrypted_content` as an account-neutral payload rejection.

## 2. Verification

- [x] 2.1 Unit tests: account-scoped keys reuse and regenerate summaries; model restriction still blocks.
- [x] 2.2 Integration tests: paused, rate-limited and quota-exhausted producers hand off on another account; an
  exhausted pool returns the ordinary selection error; a replacement rejection surfaces unchanged without a health
  write; an account-scoped key hands off on its permitted account; the handoff log names the conversation.
