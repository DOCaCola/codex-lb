## ADDED Requirements

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against client and conversation before routing. Completed thinking SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking from outbound projection while preserving visible text and paired tools and leaving retained history unchanged. It SHALL record an omission count without content or credentials. Active reasoning and server search SHALL remain account/model-bound. A subsequent explicit user message, not a tool output, SHALL mark earlier thinking completed. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active reasoning

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client or conversation
- **THEN** preparation fails before upstream dispatch
