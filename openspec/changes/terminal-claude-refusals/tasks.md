# Tasks

## 1. Terminal refusal

- [x] 1.1 Fail a translated refusal as `response.failed` with `invalid_prompt` and a category/explanation message; non-streaming Responses and Chat return 400 `invalid_request_error`; verify streaming, non-streaming and Chat.
- [x] 1.2 Keep native passthrough refusals as incomplete terminals.

## 2. Stream policy

- [x] 2.1 Hold completed tool calls and later events until the stop reason; release them for non-refusal stops and discard them with contiguous sequence numbers on refusal.
- [x] 2.2 Log the bounded refusal category, withheld count and delivered-output flag without explanation prose or content; log malformed stops as `invalid`.

## 3. Refused history

- [x] 3.1 Record a hashed client-scoped refused response before terminal delivery when output was committed.
- [x] 3.2 Omit items of recorded refused responses from translated preparation and refresh their retention; verify a follow-up carries no refused reasoning or `(continue)`, while completed responses are still replayed.

## 4. Source failure logging

- [x] 4.1 Record the source's failure code and message on failure-terminal request-log rows, keeping the generic code when none is supplied.

## 5. Verification

- [x] 5.1 Run Claude and source-dispatch regressions, lint, format, type and strict spec validation; do not deploy.
