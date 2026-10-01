## ADDED Requirements

### Requirement: Request operations remain independent of workload and model

Request logs SHALL retain server-classified request operations separately from model, transport and workload kind. Classification MUST preserve the original ingress operation through adapters, retries, streaming, detached persistence and reused upstream sessions. Operations SHALL cover Responses, Chat Completions, Messages, token count, compaction, images, transcription, embeddings, files, standalone search, thread goals, memory summarization, analytics, safety, identity keys and realtime operations. Classification MUST NOT read request content or trust client classification headers. Historical records without retained operation SHALL remain unknown. Existing workload-based accounting and privacy rules MUST remain unchanged.

#### Scenario: Standalone search
- **WHEN** the standalone alpha/search operation succeeds or fails
- **THEN** its retained operation identifies Web search without a fabricated model or usage

#### Scenario: Translated image operation
- **WHEN** an image edit is implemented with an upstream Responses request
- **THEN** the log still identifies Image edit

#### Scenario: Reused session attribution
- **WHEN** requests with different ingress operations reuse an upstream session
- **THEN** each log retains its own operation regardless of the worker's original context

#### Scenario: Unknown historical operation
- **WHEN** a retained row has no operation metadata
- **THEN** its ingress operation remains unknown without guessing from model names

### Requirement: Request types reuse the model-cell workload label area

The shared request table SHALL display localized operation labels in the existing secondary line beneath Model, alongside applicable workload labels such as Warmup or Prewarm. It MUST NOT add a request-type table column. Details SHALL expose the operation separately from workload. Dashboard parsing MUST accept the existing count_tokens workload kind. Missing model, usage and cost MUST remain missing rather than be manufactured by classification.

#### Scenario: Responses warmup
- **WHEN** a Responses operation is a warmup
- **THEN** the model-cell secondary line identifies Responses and Warmup

#### Scenario: Search without a model
- **WHEN** a Web search log has no model
- **THEN** its model cell retains the missing-model marker and displays Web search beneath it

#### Scenario: Token count
- **WHEN** a native Messages token-count log is returned
- **THEN** the dashboard accepts it and displays Token count without altering cost coverage
