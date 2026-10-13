## MODIFIED Requirements

### Requirement: Automatic Claude token capabilities
Claude model selections SHALL contain model identifiers only. Token limits SHALL derive from authenticated discovery with explicitly maintained model metadata for absent fields. Discovery SHALL take precedence. Unknown models missing either limit SHALL remain unavailable with a diagnostic. The dashboard SHALL NOT display token editors or a limits summary for Claude selections. Existing selected IDs SHALL survive upgrade, but old manual limits MUST NOT remain active. Native explicit output budgets SHALL be accepted within the effective model ceiling; omitted translated budgets SHALL use the lesser of 64000 and the resolved model maximum. Client catalogs SHALL advertise the resolved input capacity as both the default context and max_context_window, with 95% effective context and no auto-compaction threshold, so the Codex client derives compaction from the reported window. This policy SHALL apply to existing projections at catalog construction without altering persisted capabilities. A smaller working window is set only through the shared model catalogue override.

#### Scenario: Discovered limits
- **WHEN** discovery reports 1000000 input and 128000 output tokens
- **THEN** provider capability remains 1000000/128000 while clients receive 1000000 default and maximum context, 95% effective context and no compaction threshold

#### Scenario: Smaller model capacity
- **WHEN** discovery reports 200000 input tokens
- **THEN** the default and maximum context remain 200000 with no compaction threshold

#### Scenario: Existing account projection
- **WHEN** an existing projection contains a 1M capacity and an old compaction hint
- **THEN** catalog construction advertises the 1M capacity without a compaction threshold and without rewriting its provider capability

#### Scenario: Unknown limits
- **WHEN** a model lacks discovered and maintained limits
- **THEN** it cannot be newly enabled and no guessed limit is advertised

#### Scenario: Obsolete override
- **WHEN** a model-selection update contains a manual token limit
- **THEN** it is rejected rather than silently stored or ignored
