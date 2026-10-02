## MODIFIED Requirements

### Requirement: Request logs persist requested, actual, and billable service tiers separately
For Responses proxy traffic, the system MUST persist the operator-requested tier, the upstream-reported actual tier when available, and the effective billable tier used for pricing as separate request-log fields.

The legacy `fast` alias MUST be normalized to the canonical upstream value
`priority` before forwarding and before it is stored as the requested tier.
The upstream-reported `response.service_tier`, when present, MUST be stored
unchanged as the actual tier.

The billable tier MUST be settled from the requested and actual tiers by cost
rank (flex < default = auto < priority < ultrafast). The actual tier MUST only
lower the billable tier: it replaces the requested tier when it is a known tier
that is not more expensive, except that a cheaper `default` or `auto` echo MUST
NOT replace the requested tier, because the Codex backend echoes these values
on turns served on the requested tier. A missing, unknown or more expensive
actual tier MUST leave the requested tier billable.

Request logs persisted before this rule whose billable tier is an echoed
`default` or `auto` for a `priority` request MUST be re-billed at the requested
tier, with the cost difference and tier change mirrored exactly into every
folded usage aggregate.

#### Scenario: Upstream echoes the default tier on a priority request
- **WHEN** a client sends a Responses request with `service_tier: "priority"`
- **AND** the upstream response later reports `service_tier: "default"` or `"auto"`
- **THEN** the persisted request log entry records `requested_service_tier = "priority"`
- **AND** the persisted request log entry records the reported `actual_service_tier`
- **AND** the persisted request log entry records billable `service_tier = "priority"`

#### Scenario: Upstream reports a downgraded actual tier
- **WHEN** a client sends a Responses request with `service_tier: "priority"`
- **AND** the upstream response later reports `service_tier: "flex"`
- **THEN** the persisted request log entry records `actual_service_tier = "flex"`
- **AND** the persisted request log entry records billable `service_tier = "flex"`

#### Scenario: Fast alias is logged as a priority request
- **WHEN** a client sends a Responses request with `service_tier: "fast"`
- **AND** the upstream response later reports `service_tier: "default"`
- **THEN** the persisted request log entry records `requested_service_tier = "priority"`
- **AND** the persisted request log entry records `actual_service_tier = "default"`
- **AND** the persisted request log entry records billable `service_tier = "priority"`

#### Scenario: Upstream omits the actual tier
- **WHEN** a client sends a Responses request with `service_tier: "priority"`
- **AND** the upstream response omits `service_tier`
- **THEN** the persisted request log entry records `requested_service_tier = "priority"`
- **AND** the persisted request log entry records `actual_service_tier = null`
- **AND** the persisted request log entry records billable `service_tier = "priority"`

#### Scenario: Upstream reports an unknown actual tier
- **WHEN** a client sends a Responses request with `service_tier: "priority"`
- **AND** the upstream response reports a tier outside the known cost ranks
- **THEN** the persisted request log entry records `requested_service_tier = "priority"`
- **AND** the persisted request log entry records billable `service_tier = "priority"`

#### Scenario: Historical echoed tiers are re-billed
- **WHEN** a retained request log for a `priority` request carries an echoed `default` billable tier and a standard-rate cost
- **THEN** the row is re-billed with `service_tier = "priority"` and the priority-rate cost
- **AND** lifetime, report, hourly and demand aggregates change by exactly the cost difference, with hourly tier buckets moved and request counts unchanged
- **AND** repeating the repair changes nothing
