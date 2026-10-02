## MODIFIED Requirements

### Requirement: Request logs distinguish actual and requested service tiers
When a request log entry includes service-tier data, the dashboard request-log API response MUST expose the billable tier, requested tier, and actual tier separately. The recent-requests UI MUST present the billable tier: Fast (`priority`) and Ultrafast as a grey tier icon next to the reasoning effort, other non-standard tiers as muted text, and the standard `default`/`auto` tier not at all. The UI MUST show a downgrade note only when the billable tier is cheaper than the requested tier.

#### Scenario: Dashboard shows upstream-selected tier and requested tier
- **WHEN** a request log entry is recorded with `requested_service_tier: "priority"`, `actual_service_tier: "default"`, and billable `service_tier: "priority"`
- **THEN** the `GET /api/request-logs` response includes `requestedServiceTier: "priority"`, `actualServiceTier: "default"`, and `serviceTier: "priority"`
- **AND** the dashboard renders the grey Fast icon next to the model label
- **AND** no downgrade note is shown

#### Scenario: Proven downgrade
- **WHEN** a request log entry is recorded with `requested_service_tier: "priority"` and billable `service_tier: "flex"`
- **THEN** the dashboard shows that Fast was requested and Flex was billed
