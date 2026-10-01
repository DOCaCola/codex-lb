## ADDED Requirements

### Requirement: Weekly consumer estimated API costs

Weekly pace top-consumer rows SHALL display compact USD estimated API costs for
the same trailing two-hour window as their usage. Costs SHALL use recorded
request costs across all models and existing coverage rules, never a quota-credit
conversion. Unknown, free and incomplete costs SHALL remain distinct, with
incomplete details in tooltips. Rankings, runway calculations and privacy rules
SHALL remain unchanged.

#### Scenario: Multiple models and partial coverage
- **WHEN** a consumer has two priced requests costing $1 and $2 and one unpriced request within the attribution window
- **THEN** its row displays $3.00 with incomplete coverage in the tooltip
- **AND** request counts, tokens and dominant-model selection keep their existing semantics

#### Scenario: Unknown versus free
- **WHEN** one consumer has no known prices and another has explicitly free metered requests
- **THEN** their rows display Unknown and $0.00 respectively

#### Scenario: Responsive presentation
- **WHEN** long consumer names, model names and cost totals are shown at desktop or narrow mobile widths
- **THEN** cost remains readable without causing horizontal page overflow

### Requirement: Concise dashboard account subtitles

Dashboard account cards SHALL omit model-selection counts and All models labels
from their subtitles. They SHALL retain known provider/plan identity and use the
middle-dot separator between multiple fields, including optional account IDs.
Shared card anatomy, privacy and account actions SHALL remain unchanged. Model
selection controls elsewhere SHALL remain available.

#### Scenario: Provider card subtitles
- **WHEN** Codex Plus, paid OpenRouter and Claude Pro accounts are shown
- **THEN** their subtitles read Plus, OpenRouter · Paid and Claude · Pro respectively, without selected-model counts
