## Implementation
- [x] Track the previous completed message per account and conversation, with send ordering and a 1-hour lifetime.
- [x] Send `diagnostics` and the cache-diagnosis beta on translated Messages requests.
- [x] Log Anthropic's miss reason from message_start, message_delta and non-streamed messages.
- [x] Exclude `diagnostics` from the miss logger's parameter digests.
- [x] Tests: wire field and beta across two turns, unfinished turn is not a reference, isolation, expiry, ordering, logging.
- [x] Validate specs, lint, types and the Claude suites.
