## 1. Backend

- [x] 1.1 Advertise real source capacity as default and maximum; drop the
  Claude 272k default and compaction hints.
- [x] 1.2 Derive OpenRouter limits from the provider catalog and remove
  per-selection context/output caps.
- [x] 1.3 Migrate stored OpenRouter selections and force re-projection.
- [x] 1.4 Clamp overrides to the model ceiling; source models always clamp.
- [x] 1.5 List enabled text models in the overrides API; reject overrides for
  unlisted models or above the maximum.

## 2. Dashboard

- [x] 2.1 Rework Settings → Model catalogue into a table of enabled models
  with default, maximum and override columns.
- [x] 2.2 Remove OpenRouter cap inputs and the Claude limits line.

## 3. Verification

- [x] 3.1 Unit, integration and frontend tests for catalog projection,
  override validation, migration and settings UI.
- [x] 3.2 Deploy and set 350000 overrides for active Claude models.
