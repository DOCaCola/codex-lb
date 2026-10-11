## MODIFIED Requirements

### Requirement: Translated cache boundaries
Translated Responses SHALL produce deterministic ephemeral cache boundaries for stable instruction/tool prefixes and recent history, within Anthropic's four-breakpoint limit. When OAuth relocates the instructions into a conversation `system` turn, that turn SHALL carry its own boundary. The two rolling boundaries SHALL go on the last two user turns, except that a content-bearing `system` turn ending the request SHALL take the newest of them. Proxy-generated boundaries SHALL use the 1-hour tier (`ttl: "1h"`) that Claude Code sends, and translated requests SHALL negotiate `extended-cache-ttl-2025-04-11`. All proxy-generated boundaries share that tier, so no longer TTL follows a shorter one. Native caller markers, native betas and signed server content MUST remain unchanged. Projection MUST NOT mutate retained logical history.

#### Scenario: Subsequent translated turn
- **WHEN** a translated conversation adds another user turn
- **THEN** stable prefix and recent user-turn cache boundaries are present without changing prior text or signed blocks

#### Scenario: First request caches relocated instructions
- **GIVEN** a translated OAuth request whose messages are a user turn and a developer `system` turn
- **WHEN** the request is prepared
- **THEN** boundaries sit on `system`, the user turn, the relocated instruction turn and the developer turn, and on no other block

#### Scenario: Later turns keep the instruction boundary
- **GIVEN** a translated OAuth request with relocated instructions and several later user turns
- **WHEN** the request is prepared
- **THEN** boundaries sit on `system`, the relocated instruction turn and the last two user turns

#### Scenario: Translated boundaries survive agent pauses
- **WHEN** a translated request is prepared
- **THEN** every proxy-generated boundary is `{"type":"ephemeral","ttl":"1h"}`
- **AND** the request's `anthropic-beta` includes `extended-cache-ttl-2025-04-11`

#### Scenario: Native markers are not upgraded
- **WHEN** a native Claude Code request carries its own cache markers
- **THEN** those markers and the caller's TTLs are forwarded unchanged
