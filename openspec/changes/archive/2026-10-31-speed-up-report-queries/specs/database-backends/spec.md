## ADDED Requirements

### Requirement: Asyncpg PostgreSQL sessions disable JIT

When `database_url` resolves to a PostgreSQL backend through the asyncpg driver, the application MUST configure each
SQLAlchemy async engine connection with `jit=off` in its session settings, so that query plans with overestimated row
counts do not pay JIT compilation that exceeds their execution time.

#### Scenario: Asyncpg sessions run without JIT

- **GIVEN** `database_url` uses `postgresql+asyncpg://`
- **AND** the PostgreSQL server default enables JIT
- **WHEN** the application opens a new asyncpg connection through its engine configuration
- **THEN** `SHOW jit` on that connection reports `off`

#### Scenario: SQLite backends receive no JIT setting

- **GIVEN** `database_url` resolves to a SQLite backend
- **WHEN** the application creates its async engine
- **THEN** no PostgreSQL `server_settings` are configured
