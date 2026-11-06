## ADDED Requirements

### Requirement: Client output limits reach the Codex backend
Requests to the Codex backend SHALL carry the client's output limit unchanged
as `max_output_tokens`, converted from Chat and Messages limits. Compact
requests SHALL omit it. The limit SHALL NOT make a request account-bound for
replay classification. The service MUST NOT raise, lower or invent a limit.

#### Scenario: Responses client sets an output limit
- **WHEN** a Responses or `/v1/responses` request carries `max_output_tokens`
- **THEN** the upstream request carries the same `max_output_tokens`

#### Scenario: Chat and Claude Code limits are converted
- **WHEN** a Chat request carries `max_completion_tokens` or `max_tokens`, or a Messages request carries `max_tokens`
- **THEN** the upstream Responses request carries that value as `max_output_tokens`, with `max_completion_tokens` taking precedence

#### Scenario: Compaction is never capped
- **WHEN** a compact request carries `max_output_tokens`
- **THEN** the upstream compact request omits it

#### Scenario: Output limit does not pin a fresh replay
- **WHEN** a goal-restart full resend carries `max_output_tokens` and no account-scoped state
- **THEN** it remains eligible to abandon an unavailable legacy owner

#### Scenario: Cache probe stops at its own limit
- **WHEN** a cache isolation probe response ends `incomplete` with reason `max_output_tokens`
- **THEN** the probe records its input and cached token counts as a successful measurement
- **AND** an incomplete response with any other reason remains a failed probe
