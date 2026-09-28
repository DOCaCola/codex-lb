## ADDED Requirements

### Requirement: Bounded Claude overload recovery
Explicit upstream529 or503 overloaded_error MAY be retried once on the same account before generation. The retry SHALL consume the shared four-send budget and fit a ten-second recovery window from dispatch entry. Valid Retry-After SHALL be a minimum wait; absent hints SHALL use250–500ms jitter. Waiting SHALL be cancellable and own no admission or reservation. Repreparation SHALL enforce current authorization and history ownership. Overload MUST NOT trigger credential refresh, account rotation or account/provider health penalties.

The gateway SHALL inspect SSE startup within32 events,64KiB and its first-frame deadline. Only comments/pings and empty message_start metadata without positive output usage MAY precede a recoverable overloaded_error. Such error SHALL surface as529 before any public stream event. Content blocks, other generation events or positive output usage SHALL prohibit overload replay. Prelude-limit violations, generic503, connection failures and timeouts MUST NOT acquire overload retries. Exhaustion SHALL preserve the refusal and retry hint; partial generation SHALL retain normal failure/usage handling.

#### Scenario: Early SSE refusal
- **WHEN** HTTP200 contains pings followed by overloaded_error before generation
- **THEN** the failed attempt closes and may retry on the same account without publishing its events

#### Scenario: Output already started
- **WHEN** overload follows a content block or positive output usage
- **THEN** the gateway does not replay the generation

#### Scenario: Wait exceeds recovery window
- **WHEN** Retry-After cannot fit the remaining recovery window
- **THEN** the original refusal is returned without shortening its requested wait
