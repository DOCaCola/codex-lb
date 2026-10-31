## MODIFIED Requirements

### Requirement: Account list presents a single add-account entry point with a chooser dialog

The account list SHALL present account creation through a single dashed-border placeholder control
rendered at the bottom of the list. Activating it SHALL open a chooser dialog with two groups.
"Subscriptions" SHALL list Codex, Claude and Antigravity in that order, each labelled with its
provider logo and offering exactly two options, "Sign in" and "Import file". "API providers" SHALL
list OpenRouter and OpenAI-compatible, each one option with its provider logo as icon. Every option
SHALL close the chooser and open exactly one dialog for one method.

#### Scenario: Add-account placeholder opens the chooser

- **WHEN** an operator activates the "Add account" placeholder
- **THEN** the chooser shows Subscriptions (Codex, Claude, Antigravity) and API providers (OpenRouter, OpenAI-compatible)

#### Scenario: Choosing an option opens its existing flow

- **WHEN** the operator selects "Import file" under Claude
- **THEN** the chooser closes and only the Claude credential import dialog opens

## ADDED Requirements

### Requirement: Provider sign-in and import dialogs share one flow

Claude and Antigravity sign-in SHALL use the Codex browser sign-in stages: a details stage, an
authorization stage with the authorization URL, Copy, Refresh link (which starts a new flow), a
plain-text monospace paste field with Submit, and a waiting line with an expiry countdown, followed
by a success or error stage with Try again. The URL box, copy button and paste field SHALL be shared
with the Codex dialog. Credential file import SHALL be a separate dialog per provider using one
shared file area, which the Codex multi-file import uses as well.

#### Scenario: Refresh the authorization link

- **WHEN** an operator presses Refresh link during Claude sign-in
- **THEN** a new authorization flow starts and its URL replaces the previous one

#### Scenario: Sign-in fails

- **WHEN** completing an Antigravity sign-in fails
- **THEN** the dialog shows the error stage with Close and Try again

### Requirement: Provider accounts re-authenticate like Codex

Claude and Antigravity account details SHALL offer a "Re-authenticate" control with the Codex label
and icon, opening a menu with "Sign in again" and "Import credential file". Re-authentication dialogs
SHALL show the saved identity read-only instead of a name field. When a Claude re-authentication is
held for an identity mismatch, a confirmation dialog SHALL compare the saved and incoming email,
organization and plan; Cancel SHALL discard the held sign-in and "Replace saved identity" SHALL
confirm it. A matching sign-in SHALL complete without confirmation.

#### Scenario: Plan change moves the organization

- **WHEN** a Claude sign-in for the same email returns a different organization
- **THEN** the confirmation dialog highlights the organization and plan rows, and confirming completes the reconnect without another sign-in

#### Scenario: Cancel the replacement

- **WHEN** the operator cancels the confirmation
- **THEN** the held sign-in is discarded and the saved credentials stay unchanged
