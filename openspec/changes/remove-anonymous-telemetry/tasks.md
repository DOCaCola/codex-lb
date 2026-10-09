## 1. Backend

- [x] 1.1 Delete `app/modules/telemetry/` and its wiring in `app/main.py` (scheduler, router).
- [x] 1.2 Remove `telemetry_enabled`/`telemetry_endpoint` from `Settings`, `SETTING_TIERS` and `DASHBOARD_HOMES`; add both env names to `_REMOVED_SETTINGS`; lower `[settings_fields].max` to 95; drop the `KUBERNETES_SERVICE_HOST` allowlist entry for the deleted snapshot module.
- [x] 1.3 Remove the three ORM columns and add a migration that drops them (downgrade restores them empty).
- [x] 1.4 Delete telemetry tests; replace the add-migration test with a drop-migration test; remove `build_telemetry_scheduler` from scheduler stubs.

## 2. Frontend

- [x] 2.1 Remove the consent dialog, the settings card and preview, the API/hook/schema code and their tests.
- [x] 2.2 Remove telemetry fixtures and handlers from test mocks and the browser smoke.
- [x] 2.3 Remove `settings.telemetry.*` strings from every locale.

## 3. Docs and specs

- [x] 3.1 Delete `docs/telemetry.md` and its links; regenerate the settings reference.
- [x] 3.2 Validate this change strictly; on archive delete `openspec/specs/telemetry/`.

## 4. Verification

- [x] 4.1 Backend lint, type check and affected unit tests.
- [x] 4.2 Frontend `vitest run`, `eslint .`, `tsc -b`.

Verification (2026-10-09): ruff, settings-tier check, 1,205 affected backend unit tests and the
integration migration suite pass; `ty check app` reports no finding in touched files (12
pre-existing ones elsewhere); `tsc -b` and `eslint .` pass; vitest 1,899 passed. The five
vitest failures predate this change (ko/zh-CN locale parity, handler coverage for six unrelated
fork endpoints, duplicate API-key legend buttons). `test_base_ref_revisions_reads_the_graph_out_of_git`
passes once the new migration is committed.
