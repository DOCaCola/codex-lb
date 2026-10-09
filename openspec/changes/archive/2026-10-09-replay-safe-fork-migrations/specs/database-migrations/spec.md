## ADDED Requirements

### Requirement: Fork revisions are replay-safe

Every fork revision MUST derive each DDL step from the reflected schema in both
directions. An upgrade MUST create only missing tables, columns and indexes.
A downgrade MUST remove only what is present. A data rewrite MUST run only in
the branch that introduces the column it belongs to. A downgrade MUST NOT
depend on constraint names that a schema built from the ORM metadata does not
carry.

#### Scenario: A rewound ledger replays the fork revisions without effect

- **GIVEN** a database at head holding Claude accounts and model projections
- **WHEN** its ledger is stamped below the first fork revision and the runner
  upgrades to `head`
- **THEN** the upgrade MUST finish at head without DDL errors
- **AND** the Claude account state and model projections MUST be unchanged
- **AND** the schema MUST match the ORM metadata

#### Scenario: Migrated and model-built schemas downgrade below the fork revisions

- **GIVEN** a head schema built either by the migrations or from the ORM
  metadata
- **WHEN** Alembic downgrades below the first fork revision and upgrades to
  `head` again
- **THEN** both directions MUST complete on SQLite and PostgreSQL
- **AND** the final schema MUST match the ORM metadata

### Requirement: Account JSON documents use comparable PostgreSQL storage

On PostgreSQL, `accounts.selected_models`, `reasoning_restrictions` and
`reserve_usage` MUST be stored as `jsonb`, so that the schema drift check can
compare their server defaults. SQLite MUST keep its JSON storage.

#### Scenario: Drift check compares the JSON defaults

- **GIVEN** a PostgreSQL database upgraded to `head`
- **WHEN** the schema drift check runs
- **THEN** it MUST complete and report no drift for the account JSON documents
