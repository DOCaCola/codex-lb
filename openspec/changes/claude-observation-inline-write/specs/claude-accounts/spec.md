## MODIFIED Requirements

### Requirement: Live Claude quota observation
The gateway SHALL observe valid five-hour and seven-day utilization headers on physical Claude HTTP responses, including rejected attempts, before retry or stream completion. Observations SHALL be attributed to the sending source and credential generation; stale-generation or deleted-account observations MUST NOT persist. Finite nonnegative header fractions SHALL become percentages, including values above 100%; malformed, negative or nonfinite converted values SHALL leave prior evidence unchanged. The gateway MUST NOT guess alternative scales or clamp stored utilization. Missing/reset-only headers MUST NOT invent usage or extend retained usage.

Window freshness and provenance SHALL distinguish header receipt from polling. Header updates MUST NOT mark unrelated windows fresh, clear poll errors, erase model-specific windows or clear refusal cooldowns. Request-start ordering SHALL prevent older concurrent requests from replacing newer observations; expired evidence SHALL be unknown. Atomic bounded merges SHALL preserve concurrent settings/catalog updates. History SHALL record every sample whose utilization or reset deadline differs from the latest stored sample for that account/window; unchanged samples SHALL be bounded to one per account/window/minute. Observation failures MUST NOT fail or retry inference; cancellation and upstream ownership SHALL remain intact.

The observation write SHALL run inline to completion without its own timeout. Caller cancellation during the write SHALL be delivered after the write finishes.

#### Scenario: Failover attribution
- **WHEN** account A returns quota headers with 429 before account B succeeds
- **THEN** both observations belong to their respective sending accounts

#### Scenario: Partial observation
- **WHEN** headers contain only five-hour utilization
- **THEN** other windows retain their previous evidence and freshness

#### Scenario: Replaced credentials
- **WHEN** a physical response arrives after its sending credential generation was replaced
- **THEN** its quota observation is discarded

#### Scenario: Utilization overshoot
- **WHEN** a fresh five-hour utilization header contains 1.04
- **THEN** persisted usage and dashboard text report 104%, the window is exhausted, and remaining-quota bar width is zero

#### Scenario: Exhaustion within the sampling minute
- **WHEN** five-hour utilization moves from 99% to 100% 27 seconds after the 99% sample with the same reset deadline
- **THEN** history stores the 100% sample
- **AND** a repeated 100% sample within the same minute is not stored

#### Scenario: Slow observation write
- **WHEN** persisting an observation takes longer than under normal load
- **THEN** the observation is recorded and the write is not cancelled

#### Scenario: Cancelled during observation
- **WHEN** the request is cancelled while its observation is being written
- **THEN** the write completes before the cancellation propagates
