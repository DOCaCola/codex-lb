## MODIFIED Requirements

### Requirement: Direct HTTP stream continuity conflicts surface the conflict code

When a direct HTTP (SSE) stream fails closed because required continuity-owner
selection reported `continuity_owner_conflict`, the emitted `response.failed`
error envelope MUST carry the `continuity_owner_conflict` error code and the
selection's conflict message rather than the generic
`previous_response_owner_unavailable` code. The continuity fail-closed
telemetry for that failure MUST record surface `http_stream` with reason
`owner_conflict` and MUST propagate the selection error code as the upstream
error code, and the persisted request log MUST record the surfaced conflict
code. A preferred-owner selection failure without a conflict code MUST keep
the existing `previous_response_owner_unavailable` envelope and the existing
upstream error codes. Its telemetry reason MUST be `owner_account_unavailable`,
except when only the client's `previous_response_id` binds the stream and the
owner's usage limit is spent. In that case the message MUST name the limit and
its reset and tell the client to retry without `previous_response_id`, and
the telemetry reason MUST be `owner_quota_exhausted`.

#### Scenario: Conflicting continuity owners on a direct stream

- **GIVEN** a direct HTTP stream request whose required continuity-owner selection fails with `continuity_owner_conflict`
- **WHEN** the stream fails closed without a selected account
- **THEN** the SSE `response.failed` event carries error code `continuity_owner_conflict` and the selection's conflict message
- **AND** continuity fail-closed telemetry records surface `http_stream`, reason `owner_conflict`, and upstream error code `continuity_owner_conflict`
- **AND** the persisted request log records error code `continuity_owner_conflict`

#### Scenario: Owner unavailability without a conflict is unchanged

- **GIVEN** a direct HTTP stream request whose preferred continuity owner cannot be selected
- **AND** selection did not report `continuity_owner_conflict`
- **AND** the owner is not a spent owner bound only by the client's anchor
- **WHEN** the stream fails closed without a selected account
- **THEN** the SSE `response.failed` event carries `previous_response_owner_unavailable`
- **AND** continuity fail-closed telemetry records reason `owner_account_unavailable` with the existing upstream error codes

#### Scenario: Spent owner bound only by the client's anchor

- **GIVEN** a direct HTTP stream request bound to its owner only by the client's `previous_response_id`
- **AND** the owner's persisted status shows a spent usage limit
- **WHEN** the stream fails closed without selecting the owner
- **THEN** the SSE `response.failed` event carries `previous_response_owner_unavailable` with a message naming the usage limit and its reset and telling the client to retry without `previous_response_id`
- **AND** continuity fail-closed telemetry records reason `owner_quota_exhausted`
