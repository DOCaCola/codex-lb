## Why

Chat Completions function tools are non-strict when `strict` is omitted, but the
Responses API may treat an omitted flag as strict, which makes optional arguments
required. The chat-to-Responses conversion copied the omission across that
protocol boundary (Soju06/codex-lb#2691; upstream PR #2692, open).

## What Changes

- Converting a request with chat `messages` sends `strict: false` for nested and
  flat function tools whose `strict` is omitted or null.
- Explicit booleans and parameter schemas are preserved; the client's tool
  definitions are not mutated.
- Native Responses requests and Responses-shaped chat requests keep their omissions.

## Impact

- Backend: `app/core/openai/chat_requests.py`.
- Affects `/v1/chat/completions` clients such as Hermes.
