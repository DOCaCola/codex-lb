## Decisions
Retry explicit upstream529 or503 with error.type=overloaded_error only. One same-target retry per logical request; no token refresh, account rotation or health penalty. Honor Retry-After as a minimum; otherwise jitter250–500ms. Ten seconds from entry to Claude dispatch bounds eligibility to retry and wait; it does not shorten normal inference. Long instructions return the original refusal. Each attempt settles before cancellable waiting and fresh admission.

SSE startup buffers at most32 events/64KiB within the existing first-frame deadline. Only pings/comments and an empty message_start with zero/absent output tokens can precede a recoverable overload. Any other event commits the stream. Oversized or endless prelude fails without replay. Startup refusal is normalized to529; downstream events from a discarded attempt are never published. After generation begins, retain existing terminal failure and usage handling.

## References
OpenCodex shared budgets and Retry-After lower bounds; Sub2API early SSE overload classification; OmniRoute model-capacity vs provider-health distinction. Source findings are recorded in workspace-local claude-overload-recovery.tmp.md.
