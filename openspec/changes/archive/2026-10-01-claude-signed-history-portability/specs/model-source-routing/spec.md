# Spec Delta

## MODIFIED Requirements

### Requirement: Source compaction history safety
Source compaction MUST reject unresolved previous-response or conversation handles
with an actionable client error requesting materialized history. Source requests
MUST reject unreadable native compaction checkpoints rather than replace history
with a placeholder. Valid proxy-owned summaries MUST remain portable. Both the
dedicated compact endpoint and terminal compaction triggers SHALL use the selected
source for summarization. Source history MUST be materialized before dispatch
without native compact size reduction. Portable text, tool results and images
MUST NOT be omitted or shortened to meet the native compact wire budget. Source
summarization SHALL disable automatic input truncation. Unsupported state,
provider capacity refusals and incomplete output MUST return errors without a
successful compaction checkpoint or replacement of retained original history.
Native OpenAI compact wire behavior SHALL remain unchanged.
Source model request overrides MUST NOT replace compaction history/instructions,
enable tools or automatic truncation, or attach persisted continuation handles.
Claude compaction MUST authenticate signed history and SHALL prefer its original
account and model, replaying signed blocks verbatim there. Completed signed
thinking that cannot keep its signature on the selected account or model, or
whose historical signature the upstream rejects, SHALL reach the summarizer as
readable historical assistant text in original order without fabricated
signatures; completed redacted thinking, which has no readable content, SHALL
produce no wire block. Signed state in the active turn of the client-supplied
history and hosted search state MUST remain bound to their original account and
model or fail explicitly.

#### Scenario: Unresolved compact continuation
- **WHEN** source compaction includes a previous-response handle whose history cannot be resolved
- **THEN** the proxy returns a client error without dispatching a summary request

#### Scenario: Retained compact continuation
- **WHEN** source compaction includes a resolvable previous-response handle
- **THEN** the proxy materializes the history before dispatching a stateless summarization request

#### Scenario: History exceeds the native compact budget
- **WHEN** source compaction contains readable history above 100k estimated tokens
- **THEN** the summarizer receives the complete history in original order with images and tool-result contents preserved

#### Scenario: Source capacity refusal
- **WHEN** the source rejects a compact request because complete history exceeds its capacity
- **THEN** the error is returned without retrying shortened history, emitting a successful checkpoint or replacing retained original history

#### Scenario: Native compaction compatibility
- **WHEN** native OpenAI compact serialization is used
- **THEN** its existing normalization and wire-budget behavior remain active

#### Scenario: Signed Claude history on another route
- **WHEN** compaction runs on another account or model than completed signed thinking, its owner is unavailable, completed owners differ or the upstream rejects a historical signature
- **THEN** the summarizer receives that thinking as readable assistant text with all other history unchanged, without signatures from another route

#### Scenario: Signed Claude history cannot be preserved
- **WHEN** compaction contains active-turn signed state or hosted search state whose owner or model is unavailable or conflicting
- **THEN** it returns an error without dispatching or dropping that state

#### Scenario: Conflicting model overrides
- **WHEN** source request overrides replace input or enable tools, persisted continuation or automatic truncation
- **THEN** the protected compaction contract remains active while compatible generation overrides can still apply
