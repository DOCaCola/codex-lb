# Provider request-log attribution

## Purpose
Identify provider accounts consistently in request logs without conflating provider sources with native OpenAI accounts.

## Requirements

### Requirement: Provider request attribution
Request logs SHALL display a recorded provider source using its current permitted name or retained source ID, including deleted sources. Unassigned SHALL mean neither native account nor provider source identity exists. Request details SHALL expose the same attribution. Provider identity SHALL take precedence when a source ID is recorded.

#### Scenario: OpenRouter rejection
- **WHEN** an OpenRouter log has a source ID and no native account ID
- **THEN** the account cell and details identify that source rather than Unassigned

### Requirement: Provider account filters
Account filter options SHALL include provider sources present in matching logs using source-prefixed values distinct from native account IDs. Selection SHALL filter by source ID and return accurate totals, including mixed selections and deleted sources. Authorized free-text search SHALL match provider names. Names SHALL respect account-identity permissions and email privacy settings.

#### Scenario: Same ID across identity domains
- **WHEN** native and provider records share the same ID text
- **THEN** selecting source-prefixed identity matches only the provider's requests

#### Scenario: Restricted principal
- **WHEN** a principal lacks account identity permission
- **THEN** provider names are neither returned nor searchable

### Requirement: Provider accounting distinction
Provider request logs SHALL distinguish unknown cost from explicitly free usage. New Claude logs SHALL record whether their cost is an API-equivalent estimate or unpriced; historical native-Claude zero-cost rows without provenance SHALL display as unknown without rewriting stored values, while other providers using a Claude model alias retain valid costs. Claude API-equivalent estimates SHALL use the existing pricing catalog's five-minute, one-hour and supported long-context tier fields and subtract cache reads and writes from inclusive input before pricing each category once. A selected tier missing a relevant rate SHALL remain unknown. Persisted totals, detail breakdown and reservation settlement SHALL agree. Historical rows lacking cache-write detail SHALL not be silently repriced as exact. Token breakdown SHALL remain visible when price is unknown. A cost-limited API-key reservation with unpriced usage SHALL retain its reservation estimate on settlement rather than debit zero; report subtotals SHALL NOT become authoritative budget input.

#### Scenario: Unpriced cached request
- **WHEN** a Claude request reports token categories but no complete price exists
- **THEN** the dashboard shows token categories and an unknown cost, not a zero-dollar claim

### Requirement: Plain monetary subtotal formatting
Known and partial monetary subtotals SHALL use plain currency formatting without a greater-than-or-equal prefix. Incomplete coverage SHALL remain identifiable through existing descriptions, labels or tooltips. Unknown cost MUST NOT become zero, and explicitly reported zero cost SHALL remain free. Removing the display prefix MUST NOT change cost aggregation, coverage classification, pricing or non-monetary burn-rate indicators.

The dashboard cost card SHALL retain its Est. API Cost timeframe heading and show the usual estimated per-day/hour average for a known monetary estimate, without coverage-count breakdowns. Unknown or empty cost SHALL instead use a neutral API-equivalent estimate description. Incomplete period comparisons SHALL remain suppressed and detailed report coverage SHALL remain available.

API-key lifetime cost breakdown rows and API cost-trend tooltip values SHALL use compact monetary formatting without inline known/incomplete qualifiers or priced, unpriced and unmetered request counts. API-key lifetime bars and percentages SHALL show each positive recorded cost amount divided by the sum of the displayed recorded costs, including when request coverage is incomplete or historically unknown. The subtitle SHALL identify the amounts as recorded estimated cost, not complete invoiced spend. Unknown requests MUST NOT be assigned zero or invented prices. Aggregation, unknown/free classification and other coverage-sensitive report comparisons SHALL remain unchanged.

#### Scenario: Partial cost coverage
- **WHEN** a displayed monetary subtotal excludes unpriced or unmetered requests
- **THEN** the currency value has no ≥ prefix and existing incomplete-coverage information remains available

#### Scenario: Large API-key lifetime subtotal
- **WHEN** an API key has a known cost of $44,248.05 with 422859 priced, 99 unpriced and 3985 unmetered requests
- **THEN** its lifetime cost breakdown row displays $44,248.05 without a coverage-count string and shows its share of recorded estimated cost with a bar and percentage

#### Scenario: Mixed coverage across keys
- **WHEN** two keys have recorded costs of $30 and $10 and either key has unpriced, unmetered or historically unknown request coverage
- **THEN** their lifetime cost rows retain 75% and 25% shares and matching bars, labeled as shares of recorded estimated cost

### Requirement: Cost coverage across aggregates

Every cost-bearing request-log aggregate, including report windows, conversation views and API-key seven-day totals, account buckets and trend points, SHALL expose a known-cost subtotal and request coverage: priced requests (including explicit zero), unpriced requests (usage observed but price unavailable), and unmetered requests (usage unavailable). Local refusals before generation and count-token requests SHALL not dilute coverage; dispatched failures and cancellations with possible billable generation SHALL remain in scope. Mixed coverage SHALL label the subtotal incomplete, all-unknown coverage SHALL display unknown, and empty coverage SHALL display no usage. Coverage SHALL be request coverage, never a percentage of dollars. Raw and durable rollup paths SHALL use the same classification, filters, time windows, deletion and recomputation semantics. If retained records cannot prove historical coverage, the aggregate SHALL report coverage unknown without treating a known subtotal as complete. Price-dependent averages, rankings and percent shares SHALL not imply total spend under incomplete coverage.

#### Scenario: Mixed priced and unpriced usage
- **WHEN** one retained request has a known positive cost, one is explicitly free and one has metered usage but no usable price
- **THEN** the aggregate reports their known subtotal with two priced and one unpriced request and labels cost incomplete
