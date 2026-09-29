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
