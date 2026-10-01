## MODIFIED Requirements

### Requirement: Request types reuse the model-cell workload label area

The shared request table SHALL display localized special operation labels in the existing secondary line beneath Model, alongside applicable workload labels such as Warmup or Prewarm. Standard Responses and Messages operation labels SHALL be omitted from this table line, retaining workload labels alone when applicable and rendering no empty line otherwise. It MUST NOT add a request-type table column. Details SHALL expose the operation separately from workload, including Responses and Messages. Dashboard parsing MUST accept the existing count_tokens workload kind. Missing model, usage and cost MUST remain missing rather than be manufactured by classification.

#### Scenario: Responses warmup
- **WHEN** a Responses operation is a warmup
- **THEN** the model-cell secondary line identifies Warmup without Responses

#### Scenario: Search without a model
- **WHEN** a Web search log has no model
- **THEN** its model cell retains the missing-model marker and displays Web search beneath it

#### Scenario: Token count
- **WHEN** a native Messages token-count log is returned
- **THEN** the dashboard accepts it and displays Token count without altering cost coverage

#### Scenario: Ordinary client traffic
- **WHEN** a normal Responses or Messages request is shown
- **THEN** its model cell has no operation-label line while details retain its explicit operation

#### Scenario: Messages prewarm
- **WHEN** a Messages operation is a prewarm
- **THEN** its model-cell secondary line identifies Prewarm without Messages

#### Scenario: Compaction through Responses
- **WHEN** a request on the Responses path is classified as Compaction
- **THEN** the table retains the Compaction label
