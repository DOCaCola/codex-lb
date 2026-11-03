## ADDED Requirements

### Requirement: Fresh usage recovers captured quota restrictions
Manual and scheduled successful usage refreshes SHALL remove captured named quota
restrictions whose explicit fresh utilization is finite, nonnegative and below 100.
Recovery SHALL occur atomically with accepted usage publication for the same
credential generation. Missing, stale or failed readings SHALL NOT recover a
restriction. Restrictions not captured before dispatch, unknown restrictions and
entitlement restrictions SHALL remain. Retry-After deadline origin SHALL NOT
prevent recovery of a named quota restriction.

#### Scenario: Subscription upgrade restores quota
- **WHEN** a fresh usage read after an inference refusal reports five-hour usage below 100
- **THEN** the captured five-hour restriction is removed and routing can use the account
- **AND** independent entitlement restrictions remain

#### Scenario: Refusal arrives during refresh
- **WHEN** a newer refusal is persisted while a usage read is in flight
- **THEN** that restriction survives publication of the usage result
