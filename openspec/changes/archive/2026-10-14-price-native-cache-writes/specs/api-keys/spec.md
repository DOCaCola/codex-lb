## ADDED Requirements

### Requirement: Native prompt-cache writes are recorded and priced
When native Responses usage reports `input_tokens_details.cache_write_tokens`, the system MUST record the count in the request log's cache-creation tokens and MUST price those tokens at the model's cache-write rate for the effective service tier and context length. Cache writes MUST be treated as a subset of uncached input: they MUST be clamped to input tokens minus cached tokens and MUST NOT also be billed as ordinary input. When the active catalog has no cache-write price for the effective tier, writes MUST be billed at that tier's input rate. API-key usage settlement MUST use the same cache-write count as the request log.

#### Scenario: Astra write tokens use the write rate
- **GIVEN** the active catalog specifies Astra standard input, cached-input, cache-write and output rates of `10 / 1 / 12.5 / 50` USD per million tokens
- **WHEN** a standard Astra request reports 200,000 input tokens, including 100,000 cached tokens and 20,000 cache-write tokens, and no output
- **THEN** its cost is `$1.15`
- **AND** the request log records 20,000 cache-creation tokens

#### Scenario: Missing write price bills writes as input
- **GIVEN** a model whose catalog entry has no cache-write price
- **WHEN** a request reports cache-write tokens
- **THEN** the total cost equals the cost of the same usage without a cache-write count

#### Scenario: Overstated write count is clamped
- **WHEN** a request reports more cache-write tokens than its uncached input
- **THEN** only the uncached input is billed as cache writes

## MODIFIED Requirements

### Requirement: GPT-6 Astra pricing is recognized

The system MUST recognize canonical and suffixed `gpt-6-astra` model IDs when
computing API-key usage, request-log, reservation, and aggregate costs. Using
the existing input, cached-input, and output pricing model, costs per one
million tokens MUST be:

| Tier | Context | Input | Cached input | Output |
| --- | --- | --- | --- | --- |
| Standard | at most 272K input tokens | `10` | `1` | `50` |
| Standard | more than 272K input tokens | `20` | `2` | `75` |
| Flex | at most 272K input tokens | `5` | `0.5` | `25` |
| Flex | more than 272K input tokens | `10` | `1` | `37.5` |
| Fast/priority | existing supported context calculation | `20` | `2` | `100` |

The `priority` and `fast` service-tier aliases MUST use the Fast rates. Standard
long-context rates MUST apply only when input tokens exceed 272,000. Flex
long-context pricing MUST use the existing Flex long-context multipliers.
Cache-write tokens MUST be priced by the native prompt-cache write requirement.
Batch and regional-processing pricing MUST remain outside this contract because
the existing codex-lb usage model does not account for those dimensions.

#### Scenario: Astra Standard usage uses published rates

- **WHEN** an Astra request uses 200,000 input tokens, including 100,000 cached
  tokens, and produces 1,000,000 output tokens
- **THEN** Standard cost is `$51.10`

#### Scenario: Astra Fast and Flex usage use tier rates

- **WHEN** the same Astra usage uses `priority` or `fast`
- **THEN** cost is `$102.20`
- **WHEN** the same usage uses `flex`
- **THEN** cost is `$25.55`

#### Scenario: Astra long-context usage uses the published uplift

- **WHEN** a Standard Astra request uses 300,000 input tokens, including 50,000
  cached tokens, and produces 100,000 output tokens
- **THEN** cost is `$12.60`
- **WHEN** the same usage uses `flex`
- **THEN** cost is `$6.30`

#### Scenario: Suffixed Astra IDs resolve to canonical pricing

- **WHEN** cost accounting receives `gpt-6-astra-2026-09-04`
- **THEN** it resolves to the `gpt-6-astra` pricing entry
