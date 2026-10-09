## ADDED Requirements

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
Cache-write, Batch, and regional-processing pricing MUST remain outside this
contract because the existing codex-lb usage model does not account for those
dimensions.

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
