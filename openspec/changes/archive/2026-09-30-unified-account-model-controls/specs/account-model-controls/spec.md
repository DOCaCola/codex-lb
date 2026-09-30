## Purpose

Provide consistent account model availability controls while enforcing operator restrictions independently of upstream capabilities and continuity ownership.

## ADDED Requirements

### Requirement: Account model mode
All account providers SHALL expose an All models toggle and a selection dialog. Codex SHALL default to all models; Claude and OpenRouter SHALL default to explicit selection. Switching modes MUST preserve selected models and overrides. All mode MUST include newly synchronized eligible conversation models without granting unavailable upstream capabilities. OpenRouter image models MUST remain explicitly selected. Native image account selection MUST remain unchanged.

#### Scenario: Defaults and retained choices
- **WHEN** existing accounts are upgraded and an operator switches modes twice
- **THEN** Codex retains all mode, providers retain selected mode, and saved choices survive the switch

### Requirement: Native per-account model restriction
Codex account restrictions MUST apply to fresh, sticky, pinned and reused-transport selection independently of plan, quota and catalog gates. Restricted models MUST NOT be served by that account, including unknown catalog IDs. Ownership MUST NOT be silently transferred. Model controls MUST require account write permission and invalidate selection caches on successful update.

#### Scenario: Warm bridge after restriction
- **WHEN** an operator excludes a model from an account already serving a bridge session
- **THEN** subsequent requests do not bypass the restriction through that session

### Requirement: Shared provider detail layout
Codex, Claude and OpenRouter account details SHALL share usage, monitoring and action styling. Claude model selection SHALL use a dialog rather than an embedded model list, while preserving quota/reset, credential, capacity, version and reconnect controls. Read-only and pending states MUST prevent mutation.

#### Scenario: Claude detail
- **WHEN** an operator opens a Claude account
- **THEN** usage and monitoring are compact and the Models action opens its selection dialog
