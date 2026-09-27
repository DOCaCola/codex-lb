## ADDED Requirements

### Requirement: Translated hosted web search
Translated Claude Responses SHALL accept nameless web_search declarations and map supported live search options to native Anthropic search. A declaration with external_web_access=false SHALL be omitted, allowing conversation to continue without granting cached or live search through that tool. Other unsupported options MUST fail before dispatch rather than silently weaken caller constraints. HTTP and WebSocket Responses SHALL expose search lifecycle and URL citations, preserve real upstream search state across continuation, and reject missing, tampered or cross-account/model/client/conversation replay state. Server search errors and unfinished searches MUST NOT become successful completion.

#### Scenario: Default Codex search declaration
- **WHEN** Codex includes a nameless live web_search tool
- **THEN** the request reaches Claude as a versioned server-search declaration instead of failing name validation

#### Scenario: Cached-only search
- **WHEN** Codex includes web_search with external_web_access=false
- **THEN** the declaration is omitted and the remaining conversation and tools proceed without enabling live search

#### Scenario: Search continuation
- **WHEN** a client replays search output with its authenticated opaque state
- **THEN** the exact upstream search blocks are restored under the same authorized owner

#### Scenario: Missing search state
- **WHEN** a search output has no matching authenticated opaque state
- **THEN** preparation fails explicitly without dispatch

### Requirement: Translated cache boundaries
Translated Responses SHALL produce deterministic ephemeral cache boundaries for stable instruction/tool prefixes and recent user history, within Anthropic's four-breakpoint limit. Proxy-generated boundaries SHALL use the default 5m tier. Native caller markers and signed server content MUST remain unchanged. Projection MUST NOT mutate retained logical history.

#### Scenario: Subsequent translated turn
- **WHEN** a translated conversation adds another user turn
- **THEN** stable prefix and recent user-turn cache boundaries are present without changing prior text or signed blocks

### Requirement: Synthesized identity coherence
Translated Messages SHALL include a stable local device identity and the same scoped session identity in body metadata and headers. Unknown provider account identity MUST NOT be fabricated. Synthesized OS and architecture SHALL match the runtime; native reviewed headers SHALL remain caller-owned. No billing fingerprint SHALL be synthesized.

#### Scenario: Rotated credentials
- **WHEN** the selected account refreshes its token within the same client conversation
- **THEN** local device and session metadata remain stable without reusing identity across another client or account
