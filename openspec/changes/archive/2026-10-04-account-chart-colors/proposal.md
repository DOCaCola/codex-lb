# Per-account chart colours

## Why
Charts coloured accounts by their position in each chart's own list, so the same account changed colour
between the dashboard donuts and the API-key cost donut, and the colour moved whenever accounts were added or
reordered. Account logos had no colour link to the charts, and operators could not choose a colour.

## What Changes
- Codex accounts and model sources (Claude, OpenRouter and other provider accounts) store an optional chart
  colour: an index into the existing twelve-colour chart palette (six base colours and their shades).
- The backend resolves every account's colour: an explicit pick wins; other live accounts take the first
  index no pick claims, in creation order, cycling once all indices are in use.
- `GET /api/account-colors` lists resolved colours; `PUT` routes set or clear a Codex account's or model
  source's pick. API-key cost entries embed their account's resolved colour.
- Account detail headings get a colour button that opens a palette popover with an Automatic option.
- Dashboard donuts, dashboard account cards and list rows, the request log, the Accounts page list and detail
  headings, and the API-key cost donut use the resolved colour; provider logos are painted in it.

## Impact
Adds a nullable `chart_color` column to `accounts` and `model_sources`. No routing or proxy changes.
