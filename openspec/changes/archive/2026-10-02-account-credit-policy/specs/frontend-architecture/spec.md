## ADDED Requirements

### Requirement: Accounts page exposes the account credit policy
The Accounts page account settings SHALL show a Credits setting for Codex accounts with the choices "Spend credits" and "Never spend credits", plus a hint describing the selected policy's effect. The setting SHALL be hidden for accounts that need re-authentication or are deactivated. Changing it SHALL call the credit-policy endpoint and confirm the change with a toast.

#### Scenario: Reserve an account's credits
- **WHEN** an operator selects "Never spend credits" for an account
- **THEN** the dashboard sends the `never` policy and shows the updated setting
