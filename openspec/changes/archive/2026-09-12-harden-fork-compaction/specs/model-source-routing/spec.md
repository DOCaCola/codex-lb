## ADDED Requirements

### Requirement: Source compaction history safety
Source compaction MUST reject unresolved previous-response or conversation handles with an actionable client error requesting materialized history. Source requests MUST reject unreadable native compaction checkpoints rather than replace history with a placeholder. Valid proxy-owned summaries MUST remain portable.

#### Scenario: Unresolved compact continuation
- **WHEN** source compaction includes a previous-response handle
- **THEN** the proxy returns a client error without dispatching a summary request

### Requirement: Overflow compaction destination protocol
Subscription overflow with a terminal compaction trigger MUST use source synthetic compaction and preserve the overflow admission claims, attribution and settlement lifecycle.

#### Scenario: Compaction overflows to a source
- **WHEN** subscription overflow selects a source for a terminal compaction request
- **THEN** the source receives a non-streaming summarization turn and the client receives a proxy compaction envelope
