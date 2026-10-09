## MODIFIED Requirements

### Requirement: Automatic Claude token capabilities
Claude model selections SHALL contain model identifiers only. Token limits SHALL derive from authenticated discovery with explicitly maintained model metadata for absent fields. Discovery SHALL take precedence. Unknown models missing either limit SHALL remain unavailable with a diagnostic. The dashboard SHALL display resolved provider capabilities without token editors. Existing selected IDs SHALL survive upgrade, but old manual limits MUST NOT remain active. Native explicit output budgets SHALL be accepted within the effective model ceiling; omitted translated budgets SHALL use the lesser of 64000 and the resolved model maximum. Client catalogs SHALL advertise a default Claude context of the lesser of 272000 and discovered capacity, retaining actual capacity separately as max_context_window, with 95% effective context and a separate 90% default auto-compaction threshold. This policy SHALL apply to existing projections at catalog construction without altering persisted capabilities. Existing explicit context overrides SHALL retain their shared override behavior.

#### Scenario: Discovered limits
- **WHEN** discovery reports 1000000 input and 128000 output tokens
- **THEN** provider capability remains 1000000/128000 while clients receive 272000 default context, 1000000 maximum context, 244800 default compaction and 95% effective context

#### Scenario: Smaller model capacity
- **WHEN** discovery reports 200000 input tokens
- **THEN** the default and maximum context remain 200000 with 180000 default compaction

#### Scenario: Existing account projection
- **WHEN** an existing projection contains a 1M capacity and old 900000 compaction hint
- **THEN** catalog construction advertises the current conservative default without rewriting its provider capability

#### Scenario: Unknown limits
- **WHEN** a model lacks discovered and maintained limits
- **THEN** it cannot be newly enabled and no guessed limit is advertised

#### Scenario: Obsolete override
- **WHEN** a model-selection update contains a manual token limit
- **THEN** it is rejected rather than silently stored or ignored
