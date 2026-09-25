# Native OpenRouter accounts

Specification: [OpenRouter accounts](../openspec/specs/openrouter-accounts/spec.md).
Transport contract: [model-source routing](../openspec/specs/model-source-routing/spec.md).

## Setup

1. Open **Accounts → Add OpenRouter account**. Enter a name and an inference API key.
2. Optionally enter a separate management API key for account-credit monitoring. It is not used for inference.
3. Open **Models**, select the models to expose, and save. New accounts expose no models until explicitly selected.
4. Clients use `openrouter/<upstream-model-id>`. Source-restricted client keys must include the new account's source assignment.

Credentials are encrypted with the deployment's existing encryption key. Keep that key and the database together when moving the installation. Credentials never appear in account API responses.

No LiteLLM configuration is needed. Existing generic sources are not automatically deleted or imported. During a deliberate cutover, disable the old source before enabling duplicate model IDs on native accounts. Native ChatGPT accounts remain separate.

## Models and cost

Authenticated discovery uses OpenRouter's `/api/v1/models/user`. Catalog refresh runs every six hours and on **Refresh**. Prices, modalities, tool support and reasoning efforts follow the provider catalog. Context defaults to 262,144 tokens and is capped by upstream limits. Operators can set a smaller context cap, an output cap, and a display name.

Removed models retain their selection but stop routing; new models stay unselected. A failed catalog refresh retains the previous snapshot and displays an error. Concurrent updates cannot silently overwrite newer selections.

Catalog prices are estimates in USD per million tokens. The provider's `usage.cost` takes precedence in request accounting. OpenRouter's dynamic-price sentinel is shown as unknown, not free. Requests default to price-first provider selection with required-parameter support.

## Monitoring

Monitoring refreshes every minute for enabled accounts. The dashboard keeps these distinct:

- Account credits: management-key `/credits` balance, potentially shared by multiple keys.
- Key allowance: the inference key's spending cap and remaining allowance from `/key`.
- Provider usage and free-request allowance, where reported.
- Observation timestamps and errors. An unavailable value is not zero or unlimited.

## Transport and recovery

Codex can keep WebSockets enabled. The client socket terminates at codex-lb; native OpenRouter Responses requests use HTTPS/SSE upstream. The same routing, client-key policy, admission and usage settlement apply to both client transports. Custom tools and namespaces are preserved.

OpenRouter Responses is stateless: codex-lb sends `store:false` and materialized history, never an upstream `previous_response_id`. Private replay retention uses the existing one-hour TTL, 1,000-entry limit, 256 MiB per-entry limit and 1 GiB total disk budget. Completion is retained before being delivered, so immediate tool continuations can resolve it. Client identity must remain stable across reconnects. Expired or unavailable history asks the client for a full resend; it never silently discards context.

Both compact endpoints and terminal compaction triggers ask the selected model to summarize. Proxy-owned summaries remain portable; unreadable provider-specific checkpoints are rejected.

Responses requests rotate among eligible accounts serving the same model. Explicit pre-delivery 401, 402 and 429 responses can try another permitted account after the first attempt settles. Cooldowns honor Retry-After; without it they last 60 seconds. Invalid credentials and exhausted credits affect the account, while rate limiting affects the requested model. Forbidden requests, ambiguous transport failures and failures after streaming begins are not automatically replayed. The existing direct Chat Completions route remains available but does not use this Responses failover loop.

The integration tests use stub providers. A small live smoke test is still recommended before removing a production LiteLLM route, since the catalog cannot guarantee a particular provider implements every advertised tool format.
