## ADDED Requirements

### Requirement: Plain monetary subtotal formatting
Known and partial monetary subtotals SHALL use plain currency formatting without a greater-than-or-equal prefix. Incomplete coverage SHALL remain identifiable through existing descriptions, labels or tooltips. Unknown cost MUST NOT become zero, and explicitly reported zero cost SHALL remain free. Removing the display prefix MUST NOT change cost aggregation, coverage classification, pricing or non-monetary burn-rate indicators.

The dashboard cost card SHALL retain its Est. API Cost timeframe heading and show the usual estimated per-day/hour average for a known monetary estimate, without coverage-count breakdowns. Unknown or empty cost SHALL instead use a neutral API-equivalent estimate description. Incomplete period comparisons SHALL remain suppressed and detailed report coverage SHALL remain available.

#### Scenario: Partial cost coverage
- **WHEN** a displayed monetary subtotal excludes unpriced or unmetered requests
- **THEN** the currency value has no ≥ prefix and existing incomplete-coverage information remains available
