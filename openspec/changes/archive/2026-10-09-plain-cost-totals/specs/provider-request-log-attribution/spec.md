## ADDED Requirements

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
