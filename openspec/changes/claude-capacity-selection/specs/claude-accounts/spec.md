## ADDED Requirements

### Requirement: Capacity-aware Claude admission
Claude account settings SHALL expose a nullable positive-integer max_concurrency, default unlimited, enforced per worker using the existing source bulkhead. Atomic admission SHALL precede API-key reservation and inference sends. When a candidate is full, portable requests SHALL try other authorized eligible accounts, visiting each rejected candidate at most once. Hard history owners and same-account auth/overload retries MUST NOT move due to capacity. Selection exhaustion SHALL return 503 model_source_busy with Retry-After: 1. Local saturation MUST NOT consume physical-send budget, refresh credentials as error recovery, record quota cooldowns, or penalize account health. Every acquired claim SHALL retain exactly one cleanup owner and be released on cancellation, failure or completion.

Native affinity SHALL be persisted only after successful admission. Concurrent incompatible ownership changes SHALL fail before inference with a retryable claude_session_changed error, releasing admission.

#### Scenario: Soft preference is full
- **WHEN** a portable request prefers a full account and another eligible account has capacity
- **THEN** it is reprepared and sent using the available account

#### Scenario: Hard owner is full
- **WHEN** an account-bound request's owner is full
- **THEN** the gateway returns local busy without sending through another account

#### Scenario: Clearing the limit
- **WHEN** an operator clears the concurrency setting
- **THEN** the saved value is null and dispatch is unlimited
