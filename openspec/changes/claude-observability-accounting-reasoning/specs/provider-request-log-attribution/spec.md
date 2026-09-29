## MODIFIED Requirements

### Requirement: Provider accounting distinction
Provider request logs SHALL distinguish unknown cost from explicitly free usage. New Claude logs SHALL record whether their cost is an API-equivalent estimate or unpriced; historical native-Claude zero-cost rows without provenance SHALL display as unknown without rewriting stored values, while non-Claude sources using a Claude model alias retain valid costs. Claude API-equivalent estimates SHALL use the existing pricing catalog's actual 5-minute, 1-hour and supported long-context tier fields and subtract cache reads and writes from inclusive input before pricing each category once. A selected tier missing a relevant rate SHALL remain unknown. Persisted totals, detail breakdown and reservation settlement SHALL agree. Historical rows lacking cache-write detail SHALL not be silently repriced as exact. Token breakdown SHALL remain visible when price is unknown. A cost-limited API-key reservation with unpriced usage SHALL retain its reservation estimate on settlement rather than debit zero; report subtotals SHALL NOT become authoritative budget input.

#### Scenario: Unpriced cached request
- **WHEN** a Claude request reports token categories but no complete price exists
- **THEN** the dashboard shows token categories and an unknown cost, not a zero-dollar claim

### Requirement: Cost coverage across aggregates
Every cost-bearing request-log aggregate, including report windows, conversation views and API-key seven-day totals, account buckets and trend points, SHALL expose a known-cost subtotal and request coverage: priced requests (including explicit zero), unpriced requests (usage observed but price unavailable), and unmetered requests (usage unavailable). Local refusals before generation and count-token requests SHALL not dilute coverage; dispatched failures and cancellations with possible billable generation SHALL remain in scope. Mixed coverage SHALL label the subtotal incomplete, all-unknown coverage SHALL display unknown, and empty coverage SHALL display no usage. Coverage SHALL be request coverage, never a percentage of dollars. Raw and durable rollup paths SHALL use the same classification, filters, time windows, deletion and recomputation semantics. If retained records cannot prove historical coverage, the aggregate SHALL report coverage unknown without treating a known subtotal as complete. Price-dependent averages, rankings and percent shares SHALL not imply total spend under incomplete coverage.

#### Scenario: Mixed priced and unpriced usage
- **WHEN** one retained request has a known positive cost, one is explicitly free and one has metered usage but no usable price
- **THEN** the aggregate reports their known subtotal with two priced and one unpriced request and labels cost incomplete
