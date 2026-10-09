## REMOVED Requirements

### Requirement: Affected Settings dialogs restore invoker focus
**Reason**: The telemetry preview dialog it covered is removed; the password part continues as "Password setup dialog restores invoker focus".
**Migration**: None.

## ADDED Requirements

### Requirement: Password setup dialog restores invoker focus

The Settings `Set password` setup dialog SHALL retain the exact button that invoked it. When the dialog is dismissed with Escape or its explicit Cancel action, the dialog SHALL restore focus to that connected invoking button without changing the Settings page scroll position. After restoration, `document.body` MUST NOT be the active element.

Focus restoration MUST preserve the password setup flow's authentication request, session refresh, toast, form reset, and conditional mounting behavior. Password change, remove, verify, and TOTP dialogs are outside this requirement.

#### Scenario: Password setup closes with Escape

- **GIVEN** an operator opened password setup from the `Set password` button
- **WHEN** the operator presses Escape
- **THEN** the setup dialog closes without submitting password setup
- **AND** focus returns to that exact `Set password` button without scrolling Settings
- **AND** `document.body` is not active

#### Scenario: Password setup closes explicitly

- **GIVEN** an operator opened password setup from the `Set password` button
- **WHEN** the operator activates Cancel
- **THEN** the setup dialog closes without submitting password setup
- **AND** focus returns to that exact `Set password` button without scrolling Settings
- **AND** `document.body` is not active
