## ADDED Requirements

### Requirement: Dashboard provider cards follow provider order
Dashboard account cards SHALL render Codex accounts first, then Claude accounts, then OpenRouter accounts, each group in its API order.

#### Scenario: Mixed providers
- **WHEN** Codex, Claude and OpenRouter accounts exist
- **THEN** the dashboard renders Codex cards, then Claude cards, then OpenRouter cards

## MODIFIED Requirements

### Requirement: Prefer-earlier-reset and limit warm-up copy describe actual behavior

The routing settings SHALL describe `Prefer earlier reset` as preferring
otherwise-eligible accounts whose selected quota window resets sooner. The
limit warm-up feature SHALL be labeled "Window warm-up" throughout the dashboard,
and its description SHALL state that it starts opted-in accounts' usage windows
early so they reset sooner, and that its requests are real and consume a small
amount of quota. Internal API, database and request-log identifiers keep the
`limit_warmup` name.

#### Scenario: Prefer earlier reset help copy

- **WHEN** the routing settings section renders
- **THEN** the prefer-earlier-reset description says selection prefers accounts whose selected quota window resets sooner
- **AND** it names the strategies the preference applies to (capacity weighted, usage weighted, and fill first)

#### Scenario: Limit warm-up help copy

- **WHEN** the routing settings section renders
- **THEN** the feature is labeled "Window warm-up"
- **AND** its description says it starts opted-in accounts' usage windows early so they reset sooner
- **AND** it states that the requests are real and consume a small amount of quota

### Requirement: Dashboard limit warm-up controls

The dashboard SHALL expose global limit warm-up controls in Settings and per-account opt-in/status in the Accounts page account settings and the dashboard list view. Dashboard account cards SHALL NOT show limit warm-up state or controls. The global default SHALL be disabled. Settings SHALL include an exhausted-threshold percent control that determines which pre-reset usage samples count as exhausted for reset-confirmed warm-up.

#### Scenario: Configure warm-up behavior
- **WHEN** an operator opens Settings
- **THEN** the dashboard shows controls for enabling limit warm-up, selecting primary/secondary/both windows, setting the warm-up model, setting the prompt, setting the exhausted threshold, and setting the cooldown

#### Scenario: Validate warm-up settings before save
- **WHEN** an operator edits warm-up model, prompt, exhausted threshold, or cooldown fields
- **THEN** the dashboard enforces the same non-empty, max-length, percent, and integer cooldown bounds as the backend API before enabling save

#### Scenario: Show per-account opt-in and last attempt
- **WHEN** an operator selects a Codex account on the Accounts page
- **THEN** its settings show a limit warm-up switch reflecting the opt-in
- **AND** the latest attempt status, window, model, and completion/attempt time when available, or that no attempt was made

#### Scenario: Opt-in while warm-up is disabled globally
- **WHEN** global limit warm-up is known to be disabled
- **THEN** the account's warm-up switch states that nothing is sent and links to Settings

#### Scenario: Dashboard cards omit warm-up
- **WHEN** the dashboard renders Codex account cards
- **THEN** the cards show no limit warm-up state or toggle

#### Scenario: Warm-up controls are accessible by name
- **WHEN** an operator navigates the dashboard with assistive technology
- **THEN** global and per-account warm-up toggles expose descriptive accessible names that identify the setting and account context
