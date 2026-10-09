## MODIFIED Requirements

### Requirement: Every setting is assigned a configuration tier

Every configurable value SHALL belong to exactly one tier, chosen with the discriminating question "may the value legitimately differ between two replicas of the same deployment?":

| Tier | Name | Store | Restart to change | Differs between replicas | Examples |
|------|------|-------|-------------------|--------------------------|----------|
| T0 | Bootstrap | environment only | yes | no (must be identical) | data directory, database URL, encryption key file, listen port, migration policy, dashboard bootstrap token |
| T1 | Instance topology | environment only | yes | yes (legitimately) | bridge instance id / ring / advertise URL, OAuth callback host, trusted-proxy CIDRs and headers, leader election on/off, worker and pool sizes |
| T2 | Secret | encrypted database column (dashboard) with an optional environment seed | no | no | upstream proxy credentials |
| T3 | Behaviour tunable | `dashboard_settings` (or another database configuration table) | no | no | routing strategy, caps, timeouts, retries, circuit breakers, retention, feature toggles, image and model policy |
| T4 | Incident debug | environment permitted; dashboard toggle recommended | no | yes | trace channels |

The tier is decided in order: a value that is needed before the database is reachable is T0; otherwise a value that may legitimately differ between two replicas is T1 (or T4 for a debug-only channel); otherwise a credential or token is T2; every other operator-changeable value is T3. The tier of every field of `Settings` in `app/core/config/settings.py` MUST be declared in the tier registry `SETTING_TIERS` in `app/core/config/tiers.py` (field name → `"T0"` | `"T1"` | `"T2"` | `"T3"` | `"T4"`), which is the single source of the tier for the CI check (`scripts/check_settings_tiers.py`, run by `make lint`), the generated settings reference and reviewers; the tier MUST NOT be encoded in field metadata or elsewhere. A PR that adds a `Settings` field MUST add its registry entry in the same diff; a PR that removes a field SHOULD drop the entry in the same diff (a stale entry is tolerated as a warning so removals can land in either order). The number of `Settings` fields is budgeted by `[settings_fields].max` in `.github/simplicity-budgets.toml`: a PR that removes a field SHOULD lower `max` in the same diff, and a PR that adds a field MUST raise `max` in the same diff together with the P2 "why not a default" justification in its body — `max` is never raised ahead of the field it admits.

#### Scenario: Replica question places a per-instance value in the environment

- **GIVEN** a new setting whose correct value differs between two replicas (for example an advertise URL)
- **WHEN** the setting is added to `Settings`
- **THEN** it is declared T1 in `SETTING_TIERS` and lives only in the environment

#### Scenario: Replica question places a shared runtime knob in the dashboard

- **GIVEN** a new setting that must hold the same value on every replica and does not need to exist before the database is reachable (for example a stream idle timeout)
- **WHEN** the setting is added
- **THEN** it is declared T3 in `SETTING_TIERS` and is stored in `dashboard_settings` (or another database configuration table)

#### Scenario: Registry entry travels with the field

- **GIVEN** a PR that adds a `Settings` field
- **WHEN** the PR is reviewed
- **THEN** the same diff adds the field's `SETTING_TIERS` entry and raises `[settings_fields].max` by one with the P2 justification; a diff that raises `max` without adding a field, or adds a field without its registry entry, is rejected

#### Scenario: Field removal lowers the budget

- **GIVEN** a PR that deletes a `Settings` field
- **WHEN** the PR is reviewed
- **THEN** the same diff drops the field's `SETTING_TIERS` (and, if present, `MIGRATING`) entry and lowers `[settings_fields].max` by one; if the entries are dropped in a later PR instead, the interim state is a warning, not a failure

### Requirement: Precedence is code default, then environment, then dashboard

For every T3 setting the effective value MUST be resolved as: the dashboard value when it is non-NULL; otherwise the environment value when the setting has an environment fallback and the variable is set; otherwise the code default. An environment value MUST NOT override a non-NULL dashboard value, and no code path MAY invert this order (environment-wins kill switches, environment values that gate whether a dashboard value is honoured, sentinel dashboard values that defer to the environment, or `max()`/`min()` merges of environment and dashboard values are all prohibited). A field whose dashboard home is declared in `DASHBOARD_HOMES` follows the same order: the persisted value in the target column wins, the environment variable applies only while that column holds no decision. Where another capability specification currently mandates an inversion (the `rate-limit-reset-credits` polling toggle that gates `auto_redeem_reset_credits_before_expiry`), that specification MUST be amended to this precedence in the same change that removes the inversion from code; until then the inversion is a tracked defect, not an exception to this requirement.

#### Scenario: Dashboard value wins over environment

- **GIVEN** a T3 setting with a non-NULL dashboard value and a different environment value
- **WHEN** the effective value is resolved
- **THEN** the dashboard value is used

#### Scenario: Environment fills a NULL dashboard value

- **GIVEN** a T3 setting whose dashboard value is NULL and whose environment variable is set
- **WHEN** the effective value is resolved
- **THEN** the environment value is used

#### Scenario: Code default applies when neither is set

- **GIVEN** a T3 setting whose dashboard value is NULL and whose environment variable is unset
- **WHEN** the effective value is resolved
- **THEN** the code default is used

#### Scenario: Environment fallback ends when a decision is persisted

- **GIVEN** a T3 setting whose environment variable is set and whose dashboard value is NULL
- **WHEN** the operator saves a value for it in the dashboard
- **THEN** the persisted value is the effective value and the environment variable no longer applies while it stays set

### Requirement: T3 settings have a database home

Every `Settings` field declared T3 MUST have a `dashboard_settings` column of the same name, or a database home declared in the `DASHBOARD_HOMES` registry in `app/core/config/tiers.py`, or MUST be listed in the `MIGRATING` registry in the same module. A `DASHBOARD_HOMES` entry maps the field name to the existing column that holds its value when the column's name differs from the field's or lives in another database configuration table, written `table.column`; the CI check MUST verify that the column exists and MUST fail otherwise, so a home cannot be declared ahead of its column or survive the column's removal. A `MIGRATING` entry maps the field name to its target dashboard home — the column, table or existing setting the field folds into — or to the literal `"backlog"` when no home has been designed yet; an entry with any other value or an empty value is invalid. `MIGRATING` is the backlog of the environment-to-dashboard migration: the change that gives the field its column MUST delete the entry in the same diff (adding a `DASHBOARD_HOMES` entry when the column is not named after the field), and the CI check reports an entry that is redundant (the same-name column exists, `DASHBOARD_HOMES` maps the field, the field is not T3, or the field no longer exists) as a warning until it is deleted. A PR MUST NOT add a new T3 field that lives only in the environment: a new T3 field ships with its dashboard column, and a `MIGRATING` entry for a new field is accepted only when the PR body names the follow-up change that adds the column. The initial `MIGRATING` content is the set of T3 fields that were environment-only when the registry was created; it only shrinks thereafter.

#### Scenario: New environment-only tunable is rejected

- **WHEN** a PR adds a `Settings` field declared T3 with no `dashboard_settings` column of the same name, no `DASHBOARD_HOMES` mapping and no `MIGRATING` entry
- **THEN** `make lint` fails and the PR is not merged until the column exists or the field is re-tiered

#### Scenario: Migration entry names its target

- **GIVEN** a T3 field that is still environment-only
- **WHEN** it is listed in `MIGRATING`
- **THEN** the entry's value is the target dashboard column, table or setting it folds into (for example `model_context_window_overrides → backlog`, or `<field> → fold into <existing dashboard setting>` when the field folds into a setting that already has a column), or `"backlog"` when none has been designed

#### Scenario: Column lands and the entry is deleted

- **GIVEN** a T3 field listed in `MIGRATING`
- **WHEN** the change that adds its `dashboard_settings` column is merged
- **THEN** the same diff deletes the `MIGRATING` entry; if it does not, `make lint` warns that the entry is redundant until a follow-up deletes it

#### Scenario: Home under a different column name is declared explicitly

- **GIVEN** the T3 field `model_context_window_overrides`, whose persisted value is `model_context_window_overrides.context_window`
- **WHEN** the registry is checked
- **THEN** `DASHBOARD_HOMES` maps `model_context_window_overrides` to `model_context_window_overrides.context_window`, the field is not listed in `MIGRATING`, and `make lint` passes; a mapping to a column that does not exist fails the check

