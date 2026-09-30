# Provider log identity

RequestLog retains separate native account and model-source IDs. Display uses the
provider source when present, resolving current names in one batch per page.
Deleted sources retain their IDs. Names require the same account-write permission
as native account identity, and provider names are blurred in privacy mode.

Example: `accountId=source:src_router` selects logs whose model_source_id is
`src_router`; `accountId=src_router` selects native account logs instead.
Filter options expose names in accountLabels; request rows expose modelSourceName.
No historical rows are rewritten. Provider-filtered totals read raw retained logs
because demand rollups have no provider source dimension. Native/unfiltered
queries retain their existing rollup optimization.

This change covers request rows, request details, account filter options and
authorized name search. It does not change routing, retry policy, billing or
conversation-summary rollup dimensions.

Claude request costs are API-equivalent estimates from the shared pricing
catalog, not provider subscription invoices. A missing price is unknown; an
explicit zero rate is free. Cost-limited API keys with unpriced usage retain
their admission reservation estimate as the limit debit, while the request log
keeps cost unknown. Historical rows without provenance keep their stored values,
but even a stored zero is presented as unknown rather than claimed as free.

Known monetary subtotals use ordinary currency text even when coverage is
incomplete: for example, one priced $2 request and one unpriced request display
$2.00, not ≥$2.00. Existing report descriptions and tooltips retain coverage
information; unknown remains Unknown and free remains $0.00. Dashboard's
Est. API Cost (7d) card uses its usual Avg/day description instead of request
coverage counts, and incomplete period comparisons stay suppressed. This is a
presentation change, not repricing or a claim that subscription invoices equal
API-equivalent estimates. The non-monetary burn-rate lower bound is unchanged.
