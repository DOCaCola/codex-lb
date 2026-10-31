# Context

## Design decisions

- **Bars for daily values.** A day is a discrete bucket. Smoothed curves (`monotone`) suggested values between days
  and overshot below zero on queue wait; bars and straight segments through real points do not.
- **Separate token scales.** Input tokens are typically two to three orders of magnitude larger than output tokens, so
  a shared axis flattens output to zero. The trend offers them as separate metrics.
- **Neutral deltas.** More requests or more spend is not inherently good or bad, so change indicators use the muted
  foreground colour with an arrow.
- **Known-cost averages and shares.** Averages and shares use the priced subtotal. Under incomplete coverage the cost
  card and the breakdown heading carry an "incomplete" marker whose tooltip gives the priced, unpriced and unmetered
  request counts, so a subtotal is identifiable as such without a long inline note.
- **Top five plus Other.** Trend splits show the five largest series by the selected metric and sum the rest as
  Other, matching the APIs comparison chart, so colours and legends stay readable for large pools.
- **Provider-account filter.** Codex usage is attributed by `account_id`, provider-account usage by
  `model_source_id`; the filter matches either, so every row in the account breakdown can be selected.
- **Sections menu.** Visibility is per section rather than per chart. The stored IDs move to a new key; the previous
  per-chart preference is not migrated because its charts no longer exist.
