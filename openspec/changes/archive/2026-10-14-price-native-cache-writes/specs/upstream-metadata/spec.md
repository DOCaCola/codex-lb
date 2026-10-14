## MODIFIED Requirements

### Requirement: Automatic pricing metadata with offline fallbacks
The service SHALL refresh validated OpenAI text-token pricing from models.dev's public JSON, supplemented by compatible LiteLLM tier data at startup and periodically, without performing network I/O during cost calculation. It SHALL retain valid prices across partial updates and outages using a last-good persistent cache and a generated bundled snapshot before legacy code defaults. Invalid, negative, non-finite, incomplete, or non-OpenAI entries SHALL NOT replace valid prices. Exact models and their dated snapshots SHALL resolve before broad legacy aliases. Unlisted GPT-5 minor families SHALL remain unpriced until recognized instead of inheriting the generic GPT-5 price. A newer bundled snapshot SHALL take precedence over an older persistent snapshot for overlapping models. Explicit Priority/Flex and long-context rates SHALL be honored when present, including complete tier-specific long-context rates without standard long-context rates. OpenAI cache-write rates SHALL be read for each of those tiers when the source publishes them, from models.dev `cache_write` and LiteLLM `cache_creation_input_token_cost` fields; an invalid write rate SHALL invalidate the entry it belongs to. Every long-context rate group SHALL require a positive threshold. Runtime and code-generation catalog reads SHALL enforce a 16 MiB response limit before JSON parsing.

#### Scenario: New model and outage
- **WHEN** a refresh discovers GPT-6 Astra and a later refresh fails
- **THEN** subsequent requests continue using the validated Astra prices, including after restart

#### Scenario: Write rates from both sources
- **WHEN** models.dev publishes an Astra `cache_write` rate and LiteLLM publishes Priority and Flex `cache_creation_input_token_cost` variants
- **THEN** the active Astra price carries the standard, Priority and Flex cache-write rates
