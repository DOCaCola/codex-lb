## MODIFIED Requirements

### Requirement: API key cost accounting uses the billable service tier
API key cost accounting MUST use the settled billable `service_tier` recorded for the request log. An upstream-reported actual tier MUST affect pricing only when it is a proven cheaper tier; a `default` or `auto` echo on a higher requested tier MUST NOT lower the rate.

#### Scenario: Requested and actual tiers differ
- **WHEN** a priced request is sent with `requested_service_tier: "priority"`
- **AND** the upstream reports `actual_service_tier: "default"`
- **THEN** the persisted billable `service_tier` is `priority`
- **AND** API key cost accounting uses the `priority` tier rate for that request

#### Scenario: Upstream reports a cheaper non-echo tier
- **WHEN** a priced request is sent with `requested_service_tier: "priority"`
- **AND** the upstream reports `actual_service_tier: "flex"`
- **THEN** the persisted billable `service_tier` is `flex`
- **AND** API key cost accounting uses the `flex` tier rate for that request
