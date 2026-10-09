## Why
Run against PostgreSQL, the suite exposed three fork defects that SQLite masks:

- The fork revisions (`20260925_000000` onward) issued unguarded DDL. Replaying
  them over a schema that already has their changes failed with "already
  exists". That is the case for a ledger-less bootstrap and for upstream's
  retired-credential re-stamp, which replays everything after the drop
  revision. Two of them also rewrite data, so a replay would have reset Claude
  model state and rollup coverage.
- `accounts.selected_models` and `reasoning_restrictions` are PostgreSQL `json`
  with server defaults. `json` has no equality operator, so Alembic's default
  comparison raised and every schema drift check failed.
- The provider-source request-log facet had no live-row index. Its probes
  walked soft-deleted rows, because soft deletion keeps `model_source_id`.

## What Changes
- The fork revisions guard every DDL step on the reflected schema in both
  directions, as upstream revisions do. Data rewrites run only in the branch
  that introduces their column. Downgrades drop columns rather than
  constraints by name, because model-built schemas carry generated names. On
  an install that already applied them, the revisions never run again, so
  their effect there is unchanged.
- New revision `20261002_000000_account_json_documents` converts the three
  account JSON documents to `jsonb` on PostgreSQL. The ORM maps them as JSON
  with a PostgreSQL `jsonb` variant. SQLite is unchanged.
- New revision `20261002_010000_request_logs_live_source_index` adds
  `idx_logs_model_source_live` (`model_source_id WHERE deleted_at IS NULL`).
  It is built like upstream's live facet indexes and enforced through the
  manual drift index requirements. The unfiltered source facet uses the
  skip scan.

## Capabilities
### Modified Capabilities
- `database-migrations`: replay-safe fork revisions; comparable JSON storage.
- `query-caching`: the provider-source facet probes a live-row index.

## Impact
- Fork migrations from `20260925_000000_openrouter_accounts` through
  `20261001_000000_request_operation`, plus two new revisions.
- `app/db/models.py`, `app/db/migrate.py`, and
  `app/modules/request_logs/repository.py`.
- The production upgrade rewrites the small `accounts` table and builds one
  index concurrently.
