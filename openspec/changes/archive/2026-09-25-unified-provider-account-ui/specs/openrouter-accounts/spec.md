## ADDED Requirements

### Requirement: Unified account presentation
OpenRouter accounts SHALL appear in the existing dashboard account card/list collection and Accounts master/detail list, without a separate provider section. The UI SHALL use consistent surfaces, typography, status badges and privacy behavior. Provider-specific monitoring MUST retain its units, unknown/stale states and timestamps; dollar balances MUST NOT be counted as Codex subscription quotas.

#### Scenario: Mixed providers
- **WHEN** both Codex and OpenRouter accounts exist
- **THEN** both appear in the same dashboard collection in either view mode and in the same searchable Accounts list

#### Scenario: Provider selection
- **WHEN** an operator selects an OpenRouter account from the list or its dashboard details action
- **THEN** the shared detail column displays that account's monitoring, model selection and credential controls

#### Scenario: Add account
- **WHEN** an operator opens the existing add-account chooser
- **THEN** OpenRouter is available alongside the native account options

#### Scenario: Read-only and unavailable monitoring
- **WHEN** a read-only user views an OpenRouter account with unavailable or stale monitoring
- **THEN** those states remain explicit, account names follow privacy settings, and mutation controls are unavailable

#### Scenario: OpenRouter-only installation
- **WHEN** no native accounts exist but an OpenRouter account exists
- **THEN** both account pages display the provider account instead of a misleading empty state

#### Scenario: Consistent account actions
- **WHEN** an operator views an OpenRouter account's details
- **THEN** the UI offers Pause for an enabled account and Resume for a paused account using the same controls as native accounts, without a separate enabled switch
- **AND** shared actions use consistent sizing and destructive-delete styling, and mutation controls are disabled while busy or read-only
