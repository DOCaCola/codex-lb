# Attribute cost breakdowns to provider accounts

## Why
Claude and OpenRouter requests are recorded against their provider account (`model_source_id`) and carry no
Codex `account_id`. The API-key "Cost by account" breakdown and the Reports by-account and active-account
aggregates only group by the Codex `account_id`, so every non-Codex request lands in one "Unknown Account"
bucket. In production this was 9,784 requests ($1,075) over seven days. Codex accounts are labelled by email,
while the rest of the dashboard labels accounts by their display name.

## What Changes
- API-key account cost breakdowns group by provider account (Codex account or model source) and return
  `modelSourceId`, `provider` (`codex`, `claude`, `openrouter` or `null`) and a display `name` (Codex alias,
  falling back to email; model-source name) in place of `email`.
- Usage whose model source no longer exists joins the deleted-account bucket.
- Permanent report aggregates gain a model-source dimension. Reports `byAccount` entries and active-account
  counts use the provider-account identity. Retained raw history is refolded through the existing report
  repair pass; buckets older than raw retention keep their unattributed source.
- The API-key cost donut legend shows the provider logo in the slice colour; the coloured dot remains for
  entries without a known provider.

## Impact
API-key usage and reports response schemas, one migration on `request_report_hourly_rollups`, a one-time
report refold, and the shared provider logo component.
