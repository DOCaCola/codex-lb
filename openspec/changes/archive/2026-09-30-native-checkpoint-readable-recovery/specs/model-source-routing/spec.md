## ADDED Requirements

### Requirement: Verified readable native checkpoint recovery

After successful native compaction and settlement, the proxy SHALL retain complete
readable logical input under the checkpoint digest, authenticated API key and
conversation/session identity. The record SHALL use private integrity-checked
bounded storage with a one-hour lifetime. It MUST NOT retain provider ciphertext,
transport telemetry, payload-free local markers or tool advertisements. Messages,
readable reasoning, instructions, attachments and direct tool call/result identities
SHALL remain complete and ordered. Unknown semantic input, unresolved handles,
hosted resource state and unpaired outputs MUST NOT seed partial recovery records.

Source inference and summarization over HTTP and WebSocket SHALL materialize
verified checkpoints before source dispatch and continuation retention. An exact
recorded compact replacement prefix SHALL be removed only when it directly precedes
its checkpoint, preventing duplicate v1 retained messages. Repeated user turns
MUST NOT be deduplicated by content alone. Chained compacts SHALL retain a complete
materialized record independent of older records' subsequent expiry. Native wire
requests and checkpoint contents MUST remain unchanged. Missing, corrupt, evicted,
cross-scope or unobserved checkpoints MUST fail explicitly; no placeholder or
shortened-history retry SHALL be sent. Recovery diagnostics MUST contain only
request identity and aggregate counts or bounded reasons.

#### Scenario: New native checkpoint then source switch
- **WHEN** a successful native compact with complete readable input is followed by a source request using that checkpoint in the same authenticated conversation
- **THEN** the source receives complete readable context and no checkpoint ciphertext

#### Scenario: Protocol debris and semantic evidence
- **WHEN** native compact input contains advertisements, telemetry, reasoning and paired tool evidence
- **THEN** the recovery record excludes nonsemantic data and ciphertext while retaining readable reasoning, full tool evidence and attachments

#### Scenario: Exact compact replacement prefix
- **WHEN** a source replays the exact preserved-message prefix returned with a retained checkpoint
- **THEN** recovery includes those messages once and leaves unrelated repeated turns intact

#### Scenario: Unavailable or incomplete record
- **WHEN** recovery state is expired, corrupt, unobserved, from another scope or could not be retained completely
- **THEN** source preparation fails without dispatching partial history

#### Scenario: Chained native compaction
- **WHEN** a native compaction input includes a verified earlier checkpoint
- **THEN** the new record contains its materialized context and remains usable after the older record expires

#### Scenario: Native and failed compact behavior
- **WHEN** native compaction succeeds or fails
- **THEN** its existing wire result and settlement are unchanged and failed compaction does not seed recovery

## MODIFIED Requirements

### Requirement: Source local compaction marker projection

Source Responses inference and summarization SHALL distinguish payload-free local context_compaction markers from data-bearing checkpoints. A marker with missing or null encrypted_content and only recognized type, id and internal_chat_message_metadata_passthrough metadata SHALL produce no source wire item. Surrounding summaries, messages, tools and images SHALL remain ordered and unchanged, and retained logical input SHALL keep the original marker. Native OpenAI replay SHALL remain unchanged. The policy SHALL apply to public HTTP/WebSocket and expanded continuation.

Opaque native checkpoints without verified readable recovery, corrupt proxy summaries, malformed ciphertext and unsupported marker payload fields MUST fail before upstream dispatch with compaction_history_unavailable and an indexed input parameter. Failed projection MUST NOT partially replace input or fabricate summary text. Rejection diagnostics SHALL contain only request ID, input index, known compaction subtype, ciphertext presence and a bounded reason. Successful marker omission SHALL log one aggregate count, never content or raw identifiers.

#### Scenario: Local compaction then model switch
- **WHEN** a client replays a payload-free context_compaction marker and an ordinary summary to Claude
- **THEN** Claude receives the complete readable context without the marker and retained history keeps both original items

#### Scenario: Native opaque checkpoint
- **WHEN** a source request contains encrypted native compaction state without verified readable recovery
- **THEN** it fails at its original input index with content-free subtype diagnostics rather than replacing history with a note

#### Scenario: Malformed marker
- **WHEN** context_compaction carries empty or wrong-typed ciphertext or an unsupported payload field
- **THEN** preparation fails without discarding that item or sending incomplete context

#### Scenario: Native marker replay
- **WHEN** a native OpenAI request carries the same local marker
- **THEN** its native wire representation remains unchanged

#### Scenario: Continued replay and compact
- **WHEN** a retained source conversation containing a local marker is resumed or summarized
- **THEN** visible history remains available, markers do not reach the source, and no opaque checkpoint is silently omitted
