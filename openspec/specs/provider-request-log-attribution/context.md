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

API-key lifetime breakdown rows and API trend tooltip values use the same compact
formatter as API cost cards and tables. For example, $44,248.05 with partial
request coverage remains $44,248.05, without an inline request-count string that
can overflow the chart. Lifetime cost bars and percentages divide each recorded
positive cost by the sum of the displayed costs, regardless of incomplete or
historically unknown coverage. The subtitle "Share of recorded estimated cost"
defines this basis instead of claiming a complete invoice breakdown. For example,
$30 and $10 produce 75% and 25% bars even if some requests have no known price.
Unknown requests receive no invented cost. Other coverage-sensitive report
comparisons, detailed report coverage and underlying aggregate fields are unchanged.

## Request operation attribution

Operation metadata describes the ingress API, independently of the model,
downstream/upstream transports and accounting workload (`request_kind`). Reusing
workload kind would change warmup exclusions, count-token coverage and durable
rollups, so `request_operation` is a separate nullable field. Existing rows remain
unknown: a model name or HTTP transport cannot establish the original endpoint.

The canonical method/path supplies initial classification without reading payloads
or accepting client classification headers. Existing successful routing validation
refines a Responses operation to Compaction for a terminal top-level
`compaction_trigger`. There is no extra body parsing, prompt inference or payload
logging for classification. Historical `compaction`/`context_compaction` items and
embedded image/search tools remain ordinary Responses history or tools.
Pure ASGI context lives through the
stream. Persistence handoff, source dispatch and individual bridge turns snapshot
the operation so detached writes and reused upstream workers keep their own
ingress attribution. Cross-replica forwarding includes the operation in the
authenticated structured signature; an operation-bearing forward cannot use the
legacy signature-only acceptance path. Labels contain no call IDs or payloads,
and existing native realtime metadata redaction remains unchanged.

For example, a standalone alpha/search request with no model displays `--` with
`Web search` beneath it; an embedded search tool remains a `Responses` request,
not a new log row. A Responses warmup displays `Warmup`. An image edit
implemented upstream with Responses still displays `Image edit`. These labels
reuse the former Warmup line in the Model cell and do not add a table column.
Request details expose operation separately from accounting workload.

Standard Responses and Messages operations are omitted only from the table's
secondary model line to reduce routine traffic noise. A normal request renders no
empty subtitle or margin; a Messages prewarm displays Prewarm alone. Special
operations such as Compaction, Checkpoint handoff, Chat Completions and Token count
remain visible. Suppression follows the classified operation, not the model or
provider: Claude through Codex is still Responses. Explicit operation labels remain
available in request details and API/storage metadata. No routing or accounting
behavior changes.

For example, terminal compaction arriving at `/backend-api/codex/responses`
displays Compaction rather than Responses, even when a provider adapter removes
the trigger and generates a summarization request. Native websocket turns snapshot
their own validated result without changing the connection-wide operation; source
websocket turns run through the HTTP pipeline in separate turn tasks. A following
normal turn remains Responses. Internal compact calls and automation compact pings
identify their actual operation, without changing their existing workload kind.

Auxiliary native provider-switch generation displays Checkpoint handoff. Its
operation is scoped alongside the auxiliary request ID and restored on success,
error, timeout and cancellation, so a parent compaction or image operation keeps
its own label. Authenticated owner forwarding binds the refined operation to the
existing signature. No new log producer or historical correction is introduced.

Upgrade adds nullable metadata with no historical backfill. There is no new
polling or log producer, operation filter or aggregate dimension. Classification
does not change routing, account attribution, settlement, usage, pricing or
privacy rules. Missing model/token/cost values stay missing.
