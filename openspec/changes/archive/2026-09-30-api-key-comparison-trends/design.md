# Design

## Context

Individual key trends already merge watermark-consistent hourly rollups and raw complement windows. The overview contains five lifetime statistics and two lifetime breakdown cards. See proposal.md for motivation.

## Goals / Non-Goals

Goals: shared aggregation and timeline, bounded chart complexity, trustworthy cumulative totals, responsive presentation.
Non-goals: account/provider comparisons, configurable windows, new persistence or external chart libraries.

## Decisions

- Refactor the existing repository trend reader to optionally group all non-null API-key identities in one pass. Keep its rollup/raw partition unchanged; reuse it for individual trends. Fetch key names separately without loading key secrets or policies. Combine unmatched retained IDs into an anonymous deleted-keys series in the service.
- Return the full series in one collection response with window bounds. Transform top five/Other and cumulative values on the client; toggles require no network calls. Use IDs, not names, for chart data and selection. Rank by selected metric, break ties by ID, and keep colors tied to identity.
- Use the common cost-coverage formatters. Add coverage counts and OR the unknown flag when grouping Other or building running totals. Unknown-only points become null chart values; tooltips retain their metadata. Empty hours remain zero when usage exists elsewhere in that series.
- Reuse Recharts lazy components, theme palette, reduced-motion preferences, existing segmented-button styling and card spacing. Use stack areas for hourly totals and unstacked lines for cumulative comparisons. The panel is 280px tall; header and legend wrap on mobile.
- Keep the query under the existing read-permission gate with five-minute refresh, invalidated by key mutations. Surface errors with retry rather than displaying empty data.

## Risks / Trade-offs

- Hourly spikes can be dense across a week → tooltip gives precise values; cumulative mode provides a cleaner comparison.
- Keys beyond five cannot be compared individually → Other preserves the total, and per-key detail remains available.
- Missing pricing cannot produce exact costs → preserve coverage, leave unknown-only points as gaps, and use a brief informational tooltip instead of verbose labels.
- Rollups have partial boundary limitations after raw retention → inherit and document the existing reader's partition semantics.

## Migration Plan

No migration or configuration change. Deploy backend and frontend together; rollback restores the previous overview.
