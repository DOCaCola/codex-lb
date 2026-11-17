## Why

Every `/backend-api/codex/models` build logs `codex_catalog_exceeds_client_limit` at error level, about 10,000 times a day, because the catalog is now about 1.29 MB against a 1 MiB check.

The check mirrors a Codex client limit that no longer exists. Codex added a 1 MiB cap for explicit `model_catalog_url` catalogs on 2026-09-19 (openai/codex#46561) and removed it on 2026-10-23 (openai/codex#56525). Releases 0.161.0–0.165.0 enforce it; 0.166.0 and later do not. Clients that discover models through the provider's ordinary `/models` endpoint never had a cap.

The requirement also states the wrong consequence. An affected client does not use its bundled catalog: an explicit catalog URL disables that fallback, so the client keeps its last successfully fetched catalog, or has none.

In production the last 72 hours of catalog requests were almost entirely from 0.166.0 and later; one 0.164.0 client remains. The warning therefore no longer reports an actionable condition.

## What Changes

- Remove the catalog size check, its constant and its log line.
- Remove the "Codex catalog size is checked against the client limit" requirement.

## Impact

- Specs: `model-catalog-compat`.
- Code: `app/modules/proxy/api.py`; test `tests/integration/test_v1_models.py`.
- Catalog content is unchanged. Codex clients 0.161.0–0.165.0 configured with `model_catalog_url` keep rejecting catalogs above 1 MiB and should be updated to 0.166.0 or later.
