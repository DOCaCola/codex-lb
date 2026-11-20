## ADDED Requirements

### Requirement: Budget thresholds judge reported quota usage

Budget thresholds and usage exhaustion MUST be judged on the usage upstream reported, excluding runtime in-flight pressure. This applies to sticky budget-pressure reallocation, exhausted soft-owner release and the budget-safe candidate preference. Runtime pressure MAY rank candidates within the routing strategy but MUST NOT make an account over budget or exhausted, and MUST NOT by itself rebind or delete a sticky-session mapping.

#### Scenario: Busy soft owner below the threshold keeps its conversation

- **GIVEN** a prompt-cache thread mapping points to account A
- **AND** account A reports 84% weekly usage and holds five open stream leases
- **AND** account B reports 1% weekly usage
- **AND** the sticky thresholds are 95%
- **WHEN** a reconnecting request for that thread is selected
- **THEN** the request is served by account A
- **AND** the mapping still points to account A

#### Scenario: Soft owner over the threshold is still released

- **GIVEN** a prompt-cache thread mapping points to account A
- **AND** account A reports usage above a sticky threshold
- **AND** account B reports usage at or below both sticky thresholds
- **WHEN** a request for that thread is selected
- **THEN** selection rebinds the mapping to account B

#### Scenario: Busy account under budget stays budget-safe for fresh selection

- **GIVEN** account A reports 65% primary usage and holds five open stream leases
- **AND** account B reports 72% primary usage
- **AND** the budget threshold is 70%
- **WHEN** a request without a sticky mapping is selected
- **THEN** account A is preferred as the only budget-safe candidate
