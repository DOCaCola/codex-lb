## MODIFIED Requirements

### Requirement: Dashboard quota provider toggle
The dashboard SHALL group the 5-hour, weekly, weekly pace and Top consumers cards in a Quota section with a provider toggle offering Codex and each of Claude and Antigravity that has at least one account. The toggle SHALL switch all four cards together, persist with the dashboard preferences, and be hidden when Codex is the only option. A stored provider without accounts SHALL show Codex. The cards SHALL lay out in four columns on wide screens, two on medium and one on narrow screens.

#### Scenario: No Claude accounts
- **WHEN** no Claude or Antigravity account is configured
- **THEN** the toggle is not shown and the cards show Codex

#### Scenario: Antigravity without Claude
- **WHEN** an Antigravity account exists and no Claude account exists
- **THEN** the toggle offers Codex and Antigravity

### Requirement: Weekly consumer estimated API costs

The dashboard SHALL show a standalone Top consumers card listing the top API keys by requests and by billable tokens over the trailing two hours, with request count, billable tokens, dominant model and compact USD estimated API cost. The overview and projections payloads SHALL provide the lists per provider (`topConsumers.codex` from native Codex requests, `topConsumers.claude` from Claude requests and `topConsumers.antigravity` from Antigravity requests), and the card SHALL show the list of the selected quota provider. Costs SHALL use recorded request costs across all models and existing coverage rules, never a quota-credit conversion. Unknown, free and incomplete costs SHALL remain distinct, with incomplete details in tooltips. Runway calculations and privacy rules SHALL remain unchanged.

#### Scenario: Provider-scoped consumers
- **WHEN** an API key sent only Claude requests in the trailing two hours
- **THEN** it appears in the Claude list and not in the Codex list

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
