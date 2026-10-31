# Provider Observability

## Purpose

Explain actual routing exclusions and measured provider activity through existing
dashboard surfaces, without changing routing policy or retaining transcripts.

## Requirements

### Requirement: Safe routing explanations
Failed Claude selection, exhausted OpenRouter refusal failover and mixed native
account exclusions SHALL explain actual exclusion categories using safe aggregate
counts, preserving existing error codes, statuses and ownership rules.
Existing uniform native-pool and authorization failures SHALL retain their clear
specific errors rather than being replaced with an inferred exclusion report.
Known cooldown timing SHALL remain available without exposing account identities.
Unknown recovery timing MUST NOT be invented. Diagnostics MUST NOT alter ranking,
admission, failover or request dispatch.

#### Scenario: Mixed exclusions
- **WHEN** actual selection excludes candidates for different reasons
- **THEN** its error reports those category counts without account identities

### Requirement: Existing conversation analytics extension
The conversation details surface SHALL include actual provider-account counts,
errors and cancellations, measured per-model average TTFT and TPS with sample
counts, cache-write totals with measurement coverage, and an hourly activity
series bounded to the latest seven days. Missing speed samples SHALL be null.
All new data SHALL derive from existing request logs without transcript storage.
Existing conversation permissions and cost coverage semantics MUST remain intact.

#### Scenario: Provider switch and activity window
- **WHEN** a conversation uses subscription accounts and provider sources
- **THEN** its account count includes both namespaces
- **AND** its activity series identifies its bounded window independently of
  lifetime summary totals
