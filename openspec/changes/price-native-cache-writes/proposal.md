## Why
OpenAI now reports prompt-cache writes for GPT-6 models (`input_tokens_details.cache_write_tokens`) and publishes a separate write price at 1.25× input. codex-lb billed those tokens as ordinary input and did not record them, so native costs were understated and the request log could not show cache writes the way it already does for Claude.

## What Changes
- Native Responses usage parses `cache_write_tokens` and records it in the existing `request_logs.cache_creation_tokens` column on every native writer (HTTP stream, WebSocket, compact, warmup, limit warmup, quota-planner warmup).
- API-key reservations and usage settlement receive the cache-write count, so key limits and lifetime cost use the same price as the request log.
- The pricing model gains OpenAI cache-write rates for standard, Priority, Flex and their long-context variants. Writes are a subset of uncached input; they are clamped to it and billed at the write rate, and the cost breakdown reports them separately.
- The pricing catalog reads write prices from models.dev (`cache_write`, including tier overrides) and LiteLLM (`cache_creation_input_token_cost` with `_priority`, `_flex` and `_above_272k_tokens` variants). Anthropic's 5-minute and 1-hour write fields are unchanged.
- A tier whose catalog entry has no write price bills writes as that tier's input, which is what OpenAI billed before write pricing existed.

## Impact
- Specs: `api-keys` (Astra contract, new native cache-write requirement), `upstream-metadata` (catalog parses write rates).
- Code: `app/core/openai/models.py`, `app/core/usage/{pricing,pricing_catalog,logs}.py`, proxy settlement and request-log writers, API-key settlement, warmup paths.
- No migration; historical rows keep their recorded cost.
