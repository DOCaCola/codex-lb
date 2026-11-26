## Why

Replaying the fork migrations after recovering an Alembic ledger can fail when the model redirects table or request-log attribution column already exists. The schema can also contain only one of these objects after an interrupted SQLite migration.

## What Changes

- Inspect the table and column independently before applying or reversing the model redirect revision.
- Apply the same replay guarantees to the SQLite request-log attribution index.
- Verify that ledger recovery preserves stored redirects and existing request-log attribution.

## Capabilities

### Modified Capabilities

- `database-migrations` covers replay of the model redirect revision.

## Impact

The existing revisions keep their IDs, parents, schema and data. Databases already at head do not rerun them.
