## 1. API-key breakdown
- [x] 1.1 Group API-key account costs by Codex account and model source, with display name and provider.
- [x] 1.2 Treat usage of removed model sources as deleted-account usage.
- [x] 1.3 Replace `email` with `name`, add `modelSourceId` and `provider` to the API response.

## 2. Reports
- [x] 2.1 Add a sentinel-encoded `model_source_id` key to `request_report_hourly_rollups` and request a refold.
- [x] 2.2 Fold, read and rekey the new dimension.
- [x] 2.3 Group `byAccount` and count active accounts by provider account.

## 3. Frontend
- [x] 3.1 Allow `ProviderLogo` to render in a given colour.
- [x] 3.2 Show coloured provider logos in the account cost legend, keeping the dot as fallback.

## 4. Verification
- [x] 4.1 Backend unit/integration tests for both breakdowns and the refold.
- [x] 4.2 Frontend tests for legend labels and logos.
