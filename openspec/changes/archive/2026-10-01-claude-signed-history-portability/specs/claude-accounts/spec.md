# Spec Delta

## MODIFIED Requirements

### Requirement: Bounded historical signature recovery
Messages forwarding SHALL retry at most once on an upstream HTTP 400 explicitly
rejecting a thinking-block signature, before output delivery. Recovery SHALL
change only completed historical thinking, preserve active ordinary and server
tool cycles, and leave all visible content and tool pairs unchanged. Normal
translated and native requests SHALL remove that thinking. Compaction SHALL
convert historical thinking to readable text and remove redacted thinking. If
the change would leave an empty message or no safe change exists, it SHALL
return the error. Generic errors, 429s and latest-assistant-modification errors
MUST NOT trigger it.

#### Scenario: Historical rejection
- **WHEN** an upstream rejects an eligible historical thinking signature
- **THEN** one same-target recovery attempt is allowed, without changing accounts

#### Scenario: Compaction rejection
- **WHEN** an upstream rejects a historical thinking signature in a compaction request
- **THEN** the single recovery attempt carries that thinking as text so the summary keeps its readable content

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against client and conversation before routing. Completed thinking SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking from outbound projection while preserving visible text and paired tools and leaving retained history unchanged; compaction SHALL instead project completed thinking as readable historical assistant text and omit only redacted thinking. It SHALL record conversion and omission counts without content or credentials. Active reasoning and server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking completed; compaction SHALL determine this on the client-supplied history excluding its summarization instruction. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Compaction on another route
- **WHEN** compaction selects another account or model than completed thinking
- **THEN** the summarizer receives that thinking as readable assistant text in its original position, without a signature

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active reasoning

#### Scenario: Authenticated Chat tool cycle
- **WHEN** a keyed Chat client resends the complete visible history and all tool results for one live Claude tool response
- **THEN** the gateway restores only that response's genuine signed or redacted thinking under the same conversation, model and account owner
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client or conversation
- **THEN** preparation fails before upstream dispatch

## ADDED Requirements

### Requirement: Budget thinking in an unsigned open tool turn
Translated Messages requests for budget-thinking models SHALL send `thinking: {"type":"disabled"}` when the first assistant message of the open turn, which follows the last user message without a tool result, does not begin with thinking or redacted thinking. Requested effort SHALL still be validated. The decision SHALL log a content-free diagnostic. Adaptive-thinking models, user-started turns and signed open turns SHALL keep the requested thinking configuration. Native Messages MUST remain caller-owned.

#### Scenario: Foreign tool loop on Haiku
- **WHEN** Haiku 4.5 with reasoning continues tool calls whose assistant turn has no signed Claude thinking
- **THEN** that request disables thinking instead of sending a budget the upstream rejects

#### Scenario: Signed tool loop
- **WHEN** the open turn's first assistant message begins with genuine signed thinking
- **THEN** the budget thinking configuration is sent unchanged

#### Scenario: New user turn
- **WHEN** the request ends with a user message without tool results, including a wire-only continuation
- **THEN** budget thinking is enabled as requested

#### Scenario: Adaptive model
- **WHEN** an adaptive-thinking model continues an unsigned tool loop
- **THEN** the adaptive configuration is sent unchanged
