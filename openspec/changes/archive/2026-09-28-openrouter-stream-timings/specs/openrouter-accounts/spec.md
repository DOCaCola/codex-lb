## ADDED Requirements
### Requirement: OpenRouter account tier display
Dashboard cards, account lists and account details SHALL derive Free or Paid from
the key metadata's is_free_tier flag. Missing metadata SHALL show Unknown, and
retained metadata after refresh failure SHALL be marked stale. Paid MUST NOT
imply a specific Standard, Business or Enterprise subscription.

#### Scenario: Non-free key
- **WHEN** OpenRouter reports is_free_tier false
- **THEN** the account displays Paid without inferring a commercial plan

### Requirement: Friendly upstream transport labels
The dashboard SHALL display openai_compatible_http as HTTP while preserving the
underlying transport value in storage and APIs.

#### Scenario: OpenRouter upstream HTTP
- **WHEN** a request uses openai_compatible_http upstream
- **THEN** its upstream transport badge reads Up HTTP

### Requirement: Gateway-observed OpenRouter timing
OpenRouter Chat and Responses forwarding SHALL record per-attempt duration using
a monotonic clock. Streaming TTFT SHALL measure from upstream attempt start to
first nonempty generated text, reasoning or tool arguments. Metadata, keepalives,
role-only chunks and terminal/error snapshots MUST NOT fabricate TTFT. HTTP and
WebSocket clients SHALL use the same measurement path. Nonstreaming TTFT and
unobserved first output MUST remain unknown.

#### Scenario: Bookkeeping before output
- **WHEN** a stream sends creation and keepalive events before a text delta
- **THEN** TTFT records the text delta's arrival, not the earlier events

#### Scenario: No generated delta
- **WHEN** a response only contains a terminal snapshot or nonstreaming JSON
- **THEN** duration is available but TTFT and estimated generation TPS are unknown

### Requirement: Truthful OpenRouter throughput
OpenRouter generation TPS SHALL use reported total output tokens over observed
duration after first output, including reasoning tokens. Dashboard TPS SHALL be
labeled estimated. Dashboard and reports MUST exclude unsuccessful requests,
unknown timing or output usage, and generation windows shorter than one second.
Other providers' existing metrics MUST remain unchanged.

#### Scenario: Successful measurable stream
- **WHEN** a successful stream reports 100 output tokens and a two-second generation window
- **THEN** its estimated throughput is 50 tokens per second

#### Scenario: Buffered or failed turn
- **WHEN** generation spans less than one second or the request fails
- **THEN** it contributes no OpenRouter generation TPS value
