## ADDED Requirements

### Requirement: Model redirect migration preserves applied schema steps

The model redirect revision SHALL inspect `model_redirects` and `request_logs.requested_model` independently before changing either schema object.
The attribution index revision SHALL support replay and downgrade on SQLite when the index is already in its destination state.

#### Scenario: Replay preserves the completed part of an interrupted schema change

- **GIVEN** the model redirect revision is pending and either schema object already exists
- **WHEN** the migration runner upgrades the database
- **THEN** it MUST create the missing object
- **AND** it MUST preserve existing redirects and requested-model attribution.

#### Scenario: A partial downgrade resumes

- **GIVEN** the ledger still contains the model redirect revision and either schema object is absent
- **WHEN** the migration runner downgrades past the revision
- **THEN** it MUST remove the remaining object and complete the downgrade.
