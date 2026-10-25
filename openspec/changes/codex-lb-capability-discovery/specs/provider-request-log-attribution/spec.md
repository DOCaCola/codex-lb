## MODIFIED Requirements

### Requirement: Request operations remain independent of workload and model

Request logs SHALL retain server-classified request operations separately from model, transport and workload kind. Classification MUST preserve the original ingress operation through adapters, retries, streaming, detached persistence and reused upstream sessions, except semantic refinement of Responses from existing successful routing validation and the composer-prediction refinement below. Operations SHALL cover Responses, Chat Completions, Messages, token count, compaction, composer prediction, checkpoint handoff, images, transcription, embeddings, files, standalone search, thread goals, memory summarization, analytics, safety, identity keys and realtime operations. A Responses turn whose Codex turn metadata (`x-codex-turn-metadata`, sent as a header over HTTP and in `client_metadata` over WebSocket) declares `thread_source` `composer_predictions` SHALL be labelled composer prediction; compaction takes precedence. This label is diagnostic only: it MUST NOT affect routing, accounting, limits or privacy handling. Otherwise, classification MUST NOT introduce payload parsing or prompt inference or trust client classification headers. Historical records without retained operation SHALL remain unknown. Existing workload-based accounting and privacy rules MUST remain unchanged.

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

#### Scenario: Composer prediction turn
- **WHEN** a Responses turn declares the `composer_predictions` thread source in its Codex turn metadata
- **THEN** its log identifies Prediction, while a later ordinary turn on the same WebSocket remains Responses

#### Scenario: Prediction-sourced compaction
- **WHEN** a turn declaring the `composer_predictions` thread source carries a terminal compaction trigger
- **THEN** its log identifies Compaction
