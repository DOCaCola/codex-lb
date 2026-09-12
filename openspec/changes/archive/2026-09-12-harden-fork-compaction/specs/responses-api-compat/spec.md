## ADDED Requirements

### Requirement: Explicit stored-item references retain identity
Unstored input sanitization MUST preserve item_reference IDs because storage intent controls the current response, not lookup of previously stored items.

#### Scenario: Unstored response references a stored item
- **WHEN** store is false and input contains an item_reference
- **THEN** the item's required ID is preserved

### Requirement: Corrupt proxy checkpoints fail explicitly
Malformed proxy compaction envelopes MUST produce an actionable client error instead of replacing history with a placeholder.

#### Scenario: Invalid proxy checkpoint
- **WHEN** input contains a corrupt clb1 checkpoint
- **THEN** the proxy rejects the input before dispatch
