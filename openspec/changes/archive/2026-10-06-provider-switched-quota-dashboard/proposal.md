## Why
The dashboard's quota panels (5-hour and weekly donuts, weekly pace) describe only Codex credits, and the top-consumer list mixes all providers inside the Codex pace card. Operators with Claude accounts have no pooled quota view, and the activity stats sit above the accounts they summarise.

## What Changes
- Add a Quota section with a Codex | Claude toggle that switches the 5-hour ring, weekly ring, weekly pace card and a standalone Top consumers card. Hide the toggle when there are no Claude accounts.
- Pool Claude quota in Pro units using plan weights Pro 1, Max 5× 5, Max 20× 20 (display-only; routing unchanged). Accounts without a known weight or a current window observation are listed as not pooled.
- Compute a Claude weekly pace on the server with the same provider-neutral runway core as Codex, reported in `pro_units`.
- Move per-API-key top consumers out of the pace response into a per-provider `topConsumers` object.
- Move the global activity stats below the Accounts section.
- Record the provenance (`usage_api` or `inference_header`) of each Claude quota observation, because the two sources disagree by about one percentage point and interleaving them fabricated demand. Pace and demand read only usage-API observations.

## Capabilities
### Modified Capabilities
- `frontend-architecture`: weekly pace, top consumers, donut titles, quota toggle, activity placement.
- `provider-account-trends`: Claude quota observation provenance.

## Impact
Backend dashboard overview/projections schemas (`weeklyCreditPace.unit`, `claudeWeeklyPace`, `topConsumers`; `weeklyCreditPace.topApiKeys` removed), Claude account response (`quotaWeight`), one migration adding `claude_quota_history.provenance`, and the dashboard frontend. Legacy Claude history rows have no provenance and are ignored by the pace, so Claude burn and trailing demand rebuild over the following hours and days.
