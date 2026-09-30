## ADDED Requirements

### Requirement: Source local compaction marker projection

Source Responses inference and summarization SHALL distinguish payload-free local context_compaction markers from data-bearing checkpoints. A marker with missing or null encrypted_content and only recognized type, id and internal_chat_message_metadata_passthrough metadata SHALL produce no source wire item. Surrounding summaries, messages, tools and images SHALL remain ordered and unchanged, and retained logical input SHALL keep the original marker. Native OpenAI replay SHALL remain unchanged. The policy SHALL apply to public HTTP/WebSocket and expanded continuation.

Opaque native checkpoints, corrupt proxy summaries, malformed ciphertext and unsupported marker payload fields MUST fail before upstream dispatch with compaction_history_unavailable and an indexed input parameter. Failed projection MUST NOT partially replace input or fabricate summary text. Rejection diagnostics SHALL contain only request ID, input index, known compaction subtype, ciphertext presence and a bounded reason. Successful marker omission SHALL log one aggregate count, never content or raw identifiers.

#### Scenario: Local compaction then model switch
- **WHEN** a client replays a payload-free context_compaction marker and an ordinary summary to Claude
- **THEN** Claude receives the complete readable context without the marker and retained history keeps both original items

#### Scenario: Native opaque checkpoint
- **WHEN** a source request contains encrypted native compaction state
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
