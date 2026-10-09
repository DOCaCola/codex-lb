## ADDED Requirements

### Requirement: Coordinated Claude metadata refresh
Usage and catalog refreshes SHALL coordinate independently through durable per-account endpoint claims and cooldowns. Scheduled usage refresh SHALL run no more often than every three minutes and catalog refresh every six hours. Manual refresh MAY bypass successful-cache cadence but MUST NOT bypass an active claim or failed-attempt cooldown. Claims SHALL expire after bounded execution and completion SHALL require the owning claim and credential generation. Network I/O MUST NOT hold database write locks.

Last successful observations and timestamps SHALL survive failures. HTTP errors SHALL identify the metadata endpoint without exposing response bodies or credentials. Valid Retry-After seconds or HTTP dates SHALL establish the next attempt time; absent or invalid hints SHALL use three minutes. Failure on one endpoint MUST NOT prevent refreshing the other. Metadata failures MUST NOT pause accounts, penalize inference health, or trigger reactive credential rotation. Fresh inference quota headers SHALL retain their independent authority.

#### Scenario: Rate-limited usage
- **WHEN** usage returns 429 with Retry-After
- **THEN** manual and scheduled refreshes return retained state until that deadline without another usage request, including after worker restart

#### Scenario: Concurrent refresh
- **WHEN** two workers refresh the same endpoint
- **THEN** only the durable claim owner sends and a late or replaced-generation completion cannot overwrite state

#### Scenario: Endpoint isolation
- **WHEN** catalog is cooling down but usage is due
- **THEN** usage still refreshes and catalog retains its last successful data
