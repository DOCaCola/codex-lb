## MODIFIED Requirements

### Requirement: Truthful OpenRouter monitoring
The dashboard SHALL separately display account credit balance, key allowance, provider usage, free-request quota and observation timestamps when known. Unavailable monitoring MUST be shown as unknown or stale, never zero or unlimited. Account credits MUST use the management credential when configured. Observation timestamps MUST be stored and returned as UTC with an explicit offset.

#### Scenario: No management credential
- **WHEN** an inference key is configured without a management key
- **THEN** key monitoring remains available and account credit balance is unavailable

#### Scenario: Observation time in a non-UTC browser
- **WHEN** the catalog was synchronized at 09:00 UTC and the dashboard runs in Europe/Berlin during winter time
- **THEN** the account page shows the catalog as updated at 10:00
