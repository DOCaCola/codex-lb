# Proposal

## Why

Weekly credits pace identifies recent top consumers but omits their estimated
API cost. Dashboard account subtitles also use inconsistent separators and show
selected-model counts that operators do not want in the overview.

## What Changes

- Show compact estimated USD cost for each consumer over the same trailing two hours.
- Reuse recorded costs and shared coverage classification across all models.
- Keep incomplete-cost details in tooltips rather than long inline breakdowns.
- Remove selected-model counts from dashboard account subtitles and use the
  middle-dot separator for multiple identity/plan fields.
- Preserve runway calculations, rankings, account controls and model selection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-architecture`: recent-consumer cost presentation and consistent dashboard account subtitles.

## Impact

Existing dashboard attribution query/API schema, dashboard cost cells, provider
card presenters, regression tests and OpenSpec. No migration or new settings.
