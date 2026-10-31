## ADDED Requirements

### Requirement: Account notes
Every account on the Accounts page SHALL support an optional operator note of at
most 2,000 characters: Codex accounts and every model-source account (Claude,
Antigravity, OpenRouter and OpenAI-compatible). Notes SHALL be stored with the
account, listed by `GET /api/account-notes` for readers of accounts, and set by
`PUT /api/account-notes/accounts/{account_id}` or
`PUT /api/account-notes/model-sources/{source_id}` for account writers. A note
that is empty after trimming SHALL be stored as no note. Each account detail SHALL
show a Note panel under its header and status alerts with the note's text and line breaks;
writers SHALL be able to edit and save or cancel it, and read-only users SHALL see
it without edit controls. Notes SHALL NOT affect routing.

#### Scenario: Save a note
- **WHEN** a writer saves "Reserved for CI" on a Claude account
- **THEN** the Claude account detail shows "Reserved for CI" after reload

#### Scenario: Clear a note
- **WHEN** a writer saves a note containing only whitespace
- **THEN** the account has no note and its Note panel shows the empty state

#### Scenario: Read-only user
- **WHEN** a read-only user opens an account with a note
- **THEN** the note is visible without an edit control

#### Scenario: Unknown account
- **WHEN** a note is set for an account ID that does not exist
- **THEN** the API returns 404 `account_not_found`

### Requirement: Accounts page selects the first listed account
Without a valid `selected` query parameter, the Accounts page SHALL select the
first row of the account list in the list's own unfiltered order, whatever its
provider. The list and the page SHALL derive that order from one shared function.

#### Scenario: Claude listed before Codex
- **WHEN** the Accounts page opens without a selection and the list shows a Claude account above the Codex accounts
- **THEN** the Claude account is selected and highlighted

#### Scenario: Name order
- **WHEN** the list is sorted by name and an OpenRouter account comes first
- **THEN** the OpenRouter account is selected
