## ADDED Requirements

### Requirement: Native resource provenance
Native server-tool history SHALL resolve its authorized source from observed
resource origins, independently of soft session affinity. Origins SHALL be
scoped to client, conversation and model, retained for thirty days of authorized
use, and persisted before output exposing the identifier. Unknown, expired or
conflicting origins SHALL fail explicitly without inferring ownership from
affinity or incoming history. Ordinary tools and translated replay SHALL retain
their existing contracts. Count-token requests SHALL NOT create or extend origins.
Unsupported native file/container resource references SHALL fail explicitly.

#### Scenario: Affinity expires
- **WHEN** native history replays a retained resource after affinity expires
- **THEN** the request selects the resource's authorized origin account

#### Scenario: Branch rebinds
- **WHEN** different branches obtain resources on different accounts
- **THEN** each resource resolves independently and mixed-origin history fails

#### Scenario: Persistence fails
- **WHEN** a new resource origin cannot be committed
- **THEN** its identifying output is not delivered and generation is not retried

## MODIFIED Requirements

### Requirement: Native Claude affinity and signature recovery
Native first-party thinking history SHALL remain unchanged in ordinary requests.
Thinking alone MUST NOT require an unexpired account-owner record. Account
preference SHALL be subordinate to authorization and eligibility. Native server
resource state SHALL resolve observed resource origins independently of affinity.
Account rebinding MUST NOT transfer resource ownership or prevent replay of a
known resource on its authorized original account.

#### Scenario: Idle thinking conversation
- **WHEN** a native conversation resumes with thinking after affinity expires
- **THEN** it may select an eligible account without altering its thinking

### Requirement: Codex protocol adaptation
Claude SHALL support Responses over downstream HTTP and WebSocket while using HTTPS/SSE upstream. Translation MUST preserve portable text, tool/custom-tool/namespace, image, reasoning and cache-usage semantics, or reject unsupported semantics explicitly. Truncation and pause_turn MUST NOT become completed. Durable continuation MUST be persisted before terminal delivery and scoped to compatible account/model state; compaction MUST preserve useful context.

#### Scenario: Pause turn
- **WHEN** Anthropic stops with pause_turn
- **THEN** the Responses client receives an incomplete result and no hidden automatic continuation

#### Scenario: Unsupported constrained output
- **WHEN** a Responses request asks for unsupported grammar-constrained tool decoding or a provider-specific control without a Claude equivalent
- **THEN** the adapter returns an explicit unsupported-parameter error before dispatch rather than silently ignoring it

#### Scenario: Native resource history outlives provenance retention
- **WHEN** native resource history is submitted after its thirty-day resource provenance expires
- **THEN** it fails explicitly and requires portable context rather than guessing its origin from affinity
