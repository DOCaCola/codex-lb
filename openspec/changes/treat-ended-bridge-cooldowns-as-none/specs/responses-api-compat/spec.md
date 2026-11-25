## ADDED Requirements

### Requirement: HTTP bridge retry circuits do not manufacture cooldown expiries
A persisted retry-circuit cooldown that is missing, zero or elapsed SHALL load as no cooldown and MUST NOT arm a half-open probe. An expiry the worker observed for an unchanged episode SHALL still admit exactly one probe.

#### Scenario: Ended cooldown loaded from the durable row
- **GIVEN** a hard-affinity bridge key whose persisted row is at the failure threshold with an absent or elapsed cooldown
- **WHEN** requests on that key are admitted
- **THEN** each is admitted and no half-open lease is armed

#### Scenario: Watched expiry
- **GIVEN** a worker whose local cooldown for the key has run out and whose reload returns the same episode with an elapsed cooldown
- **WHEN** two requests are admitted in turn
- **THEN** the first is admitted as the probe and the second is refused while the probe is in flight
