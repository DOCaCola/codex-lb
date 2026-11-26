## Why

The ChatGPT Pro subscription includes a monthly OpenAI API credit, usable only through Platform project API keys on
`api.openai.com/v1`. It covers Responses and the Images API, including image models such as
`gpt-image-2.5-sunburst` that subscription accounts do not serve. codex-lb has no way to use that credit today, and
the image backend cannot be pointed at an API-key image model.

## What Changes

- Add an OpenAI API account type: a Platform API key whose models are published under the `openai-apikey/` prefix,
  so API-key models never mix with the subscription catalog. The prefix is removed before the request goes upstream.
- Synchronize the key's model list from `GET /v1/models`, keep new models disabled, and let operators select text
  and image models explicitly.
- Serve those models on `/v1/responses`, `/v1/chat/completions`, `/v1/messages` and `/v1/images/*`. Codex
  backend routes and the Codex model list exclude them, since OpenAI does not allow Codex usage on this credit.
- Treat OpenAI's billing refusals (`insufficient_quota`, `credit_balance_exhausted` and related codes) as account
  exhaustion: skip the account until the next credit renewal, try another eligible API-key account before any
  output is delivered, and never fall back to a subscription account.
- Let image-model redirects target OpenAI API image models, so the image backend (for example Codex's
  `gpt-image-2`) can be served by an API-key image model through the existing redirect settings.
- Estimate the remaining monthly credit on the dashboard from recorded spend, since OpenAI offers no balance
  endpoint for project keys.
- Generalize the OpenRouter cooldown and account-rotation store into a shared pooled-account store used by both
  API-key providers.

## Capabilities

### New Capabilities
- `openai-api-accounts`: API-key account lifecycle, catalog synchronization, routing, billing exhaustion, image
  serving and the credit estimate.

### Modified Capabilities
- `model-catalog-compat`: image routes resolve redirects whose source and target are image models.
- `openrouter-accounts`: the add-account chooser gains an OpenAI API group after Codex.

## Impact

New `app/modules/openai_api` module and `openai_api_accounts` table; the `openrouter_cooldowns` table becomes
`source_cooldowns`. Proxy source selection, error retry, image routes, redirect validation, pricing, dashboard
providers and the add-account dialog. No change to subscription routing or Codex clients.
