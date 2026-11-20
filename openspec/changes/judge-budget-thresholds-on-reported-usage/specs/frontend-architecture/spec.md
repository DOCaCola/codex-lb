## MODIFIED Requirements

### Requirement: Sticky thresholds are presented in percent used with a remaining equivalent

The sticky reallocation threshold controls SHALL name the quota window they
apply to, SHALL state that the value is percent used, and SHALL show the
remaining percent for a valid threshold value. Because routing judges
thresholds on the same reported usage the account pages show, the remaining
percent SHALL be presented as directly comparable to the account-page figure.

#### Scenario: Threshold unit hint

- **GIVEN** the sticky secondary threshold input holds the valid value `70`
- **WHEN** the routing settings section renders
- **THEN** a hint shows `70% used` alongside `30% remaining`
- **AND** the quota-window explainer states that thresholds compare against the reported usage the account pages show and that in-flight work only spreads new requests

#### Scenario: Quota window explainer

- **WHEN** the routing settings section renders
- **THEN** an explainer identifies primary quota as the 5-hour window and secondary quota as the longer weekly window (monthly on plans without a weekly window)
- **AND** it states that account pages show percent remaining while the thresholds are percent used
