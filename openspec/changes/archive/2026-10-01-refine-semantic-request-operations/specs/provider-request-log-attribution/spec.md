## MODIFIED Requirements

### Requirement: Request operations remain independent of workload and model

Request logs SHALL retain server-classified request operations separately from model, transport and workload kind. Classification MUST preserve the original ingress operation through adapters, retries, streaming, detached persistence and reused upstream sessions, except semantic refinement of Responses from existing successful routing validation. Operations SHALL cover Responses, Chat Completions, Messages, token count, compaction, checkpoint handoff, images, transcription, embeddings, files, standalone search, thread goals, memory summarization, analytics, safety, identity keys and realtime operations. Classification MUST NOT introduce payload parsing or prompt inference or trust client classification headers. Historical records without retained operation SHALL remain unknown. Existing workload-based accounting and privacy rules MUST remain unchanged.

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

## ADDED Requirements

### Requirement: Validated semantic operation refinement

Responses requests with a successfully validated terminal top-level compaction trigger SHALL retain Compaction before dispatch, including synthetic provider compaction. Websocket turns SHALL classify independently. Historical checkpoint items, prompt text and client metadata SHALL NOT refine the operation. Invalid triggers SHALL retain existing rejection behavior.

#### Scenario: Per-turn isolation
- **WHEN** normal, compact and normal turns share a websocket
- **THEN** their operations are Responses, Compaction and Responses respectively

#### Scenario: Synthetic compaction
- **WHEN** a provider compaction removes the validated trigger to generate a summary
- **THEN** its log retains Compaction

### Requirement: Internal executed operations

Internal compact calls and compact automation pings SHALL log Compaction. Auxiliary checkpoint handoff generation SHALL log Checkpoint handoff independently of the parent operation. Success, errors and cancellation SHALL NOT leak the auxiliary operation to the parent or concurrent requests.

#### Scenario: Nested handoff
- **WHEN** a compaction invokes a checkpoint handoff
- **THEN** the auxiliary request logs Checkpoint handoff and the parent retains Compaction
