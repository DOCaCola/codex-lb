## ADDED Requirements

### Requirement: Readable checkpoint snapshots omit reasoning configuration markers

Readable native checkpoint projection SHALL omit Codex `configuration_update` items, as it omits other protocol
control items, and SHALL retain the surrounding semantic history in order. Such an item MUST NOT make history
unreadable or prevent snapshot retention. Native OpenAI requests and replay SHALL keep the item unchanged.

#### Scenario: Compaction after a mid-thread effort change
- **WHEN** a native compaction input contains a `configuration_update` item from an effort change
- **THEN** the readable snapshot is retained without that item
- **AND** a later source request recovers the checkpoint from that snapshot
