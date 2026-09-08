## ADDED Requirements

### Requirement: HTTP replay reconstructs completed stream output
HTTP fallback replay MUST collect response.output_item.done items by output_index and reconstruct output in index order when the completed response has no non-empty output array. A non-empty terminal output array MUST remain authoritative. Collection MUST be limited to 256 items and 8 MiB of serialized item data per attempt. If collection exceeds those bounds or cannot identify a completed item, replay MUST NOT retain a partial reconstruction. Failed attempts and new response lifecycles MUST discard collected items. Reconstruction MUST NOT modify downstream stream events.

#### Scenario: Custom tool result follows an empty terminal snapshot
- **WHEN** an HTTP response emits a completed custom tool call followed by response.completed with empty output
- **AND** the next incremental request supplies its tool result
- **THEN** replay includes the matching custom tool call before the result without a previous_response_id

#### Scenario: Reconstruction exceeds its bound
- **WHEN** completed items exceed collection limits and terminal output is empty
- **THEN** no partial replay history is retained and existing missing-history recovery remains available
