## ADDED Requirements

### Requirement: Automatic Claude token capabilities
Claude model selections SHALL contain model identifiers only. Token limits SHALL derive from authenticated discovery with explicitly maintained model metadata for absent fields. Discovery SHALL take precedence. Unknown models missing either limit SHALL remain unavailable with a diagnostic. The dashboard SHALL display effective limits without token editors. Existing selected IDs SHALL survive upgrade, but old manual limits MUST NOT remain active. Native explicit output budgets SHALL be accepted within the effective model ceiling; omitted translated budgets SHALL use the lesser of 64000 and the resolved model maximum. Codex catalogs SHALL advertise the full discovered context capacity, 95% effective context, and a separate 90% auto-compaction threshold.

#### Scenario: Discovered limits
- **WHEN** discovery reports 1000000 input and 128000 output tokens
- **THEN** selecting the model advertises and enforces those values without manual entry

#### Scenario: Unknown limits
- **WHEN** a model lacks discovered and maintained limits
- **THEN** it cannot be newly enabled and no guessed limit is advertised

#### Scenario: Obsolete override
- **WHEN** a model-selection update contains a manual token limit
- **THEN** it is rejected rather than silently stored or ignored

### Requirement: Claude account presentation parity
Claude dashboard cards, account list rows and account details SHALL share the corresponding Codex quota and routing presentation components, percentage/date conventions and information hierarchy. Missing observations SHALL remain unknown, stale observations SHALL be marked, and overshoot SHALL remain observable. Claude-specific credentials, model selections and reset grants SHALL remain accessible. Unsupported OpenAI-specific information MUST NOT be fabricated. Read-only users MUST NOT mutate settings.

#### Scenario: Stale quota
- **WHEN** a Claude account has a stale weekly observation
- **THEN** its shared remaining-quota presentation includes a stale diagnostic instead of claiming fresh data

### Requirement: Claude account routing preference
Each Claude account SHALL support normal, burn_first and preserve routing policies, defaulting to normal. Authorized changes SHALL persist and appear in account views. Claude SHALL pass the policy to the shared scheduler and retain its strategy-specific semantics, authorization, hard ownership and eligible affinity; OpenAI pools MUST NOT be affected.

#### Scenario: Burn preference
- **WHEN** unbound round-robin selection has eligible normal and burn_first Claude accounts
- **THEN** the burn_first account is selected

#### Scenario: Hard owner
- **WHEN** an eligible hard owner has preserve policy and another account has burn_first
- **THEN** the owner is retained
