## MODIFIED Requirements

### Requirement: Request log models use readable names

Request-log model cells SHALL display catalog names when available and readable names for historical or uncatalogued IDs, with the exact technical ID only in the model label's native tooltip. Effort and non-default service tier SHALL appear inline in established muted grey without parentheses; default tier SHALL be omitted from that label. Requested-versus-actual differences, operation labels, filtering, stored IDs and detailed raw metadata SHALL remain unchanged.

#### Scenario: Catalog name and exact ID
- **WHEN** a request uses anthropic/claude-haiku-4-5-20251001 with high reasoning
- **THEN** its visible model label is Claude Haiku 4.5 followed by muted high without parentheses
- **AND** its native tooltip contains anthropic/claude-haiku-4-5-20251001

#### Scenario: Catalog independent rendering
- **WHEN** model catalog loading is incomplete or a historical model is absent
- **THEN** request logs remain visible with readable labels and the exact technical IDs in tooltips

#### Scenario: Standard and non-standard tiers
- **WHEN** a medium-reasoning request reports default service tier
- **THEN** its label shows the model name followed by muted medium and omits default
- **WHEN** that request reports priority service tier
- **THEN** its label also shows muted priority without parentheses

#### Scenario: No reasoning metadata
- **WHEN** a request has no reasoning effort and no non-default service tier
- **THEN** only the model name is shown without empty metadata or dangling punctuation
