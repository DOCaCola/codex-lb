## Context

A Pro subscription's monthly API credit is applied to the linked organization's project keys on
`api.openai.com/v1`. OpenAI's guide states Codex usage through API keys is not covered, and openai/codex#58005
reports that claiming the benefit can disable Codex access for that organization's keys. When the credit runs out,
OpenAI answers 429 with a billing code. There is no balance endpoint usable with a project key.

References: opencodex publishes bare names for the subscription pool and `openai-apikey/<model>` for API-key
identities, never falls back between them, and treats billing codes as scoped exhaustion bounded to six hours.
OmniRoute uses `cx/` for subscription models and `openai/` for API keys. None of the references tracks the
Platform credit balance.

## Goals / Non-Goals

Use the API credit for `/v1` clients and for image generation, keep subscription and API-key traffic strictly
separate, and show an honest estimate of the remaining credit. Not in scope: Codex backend traffic on API keys,
audio, embeddings, realtime, DALL-E models, or automatic fallback between the subscription pool and API keys.

## Decisions

- **Kind and prefix.** A `ModelSource` of kind `openai_apikey` with base `https://api.openai.com/v1`, plus an
  `openai_api_accounts` extension table (routing policy, typed state JSON, optimistic version) like OpenRouter.
  Models are published as `openai-apikey/<id>` (opencodex naming); projection maps them back to the bare id.
- **Catalog.** `GET /v1/models` validates the key and lists models. Text models are chat-capable families;
  embedding, audio, speech, transcription, moderation, realtime, legacy completion and video families are dropped.
  Image models are `gpt-image-*` and `chatgpt-image-*`, which accept the JSON Images body the native image route
  already builds. Text metadata (context window, reasoning, tools) comes from the native model registry when it
  knows the bare id; unknown models use the source defaults. Selections are explicit and new models stay disabled.
- **Pricing.** Costs use the existing API price table on the bare model id, like Antigravity.
- **Codex separation.** The Codex model list excludes `openai_apikey` models, and the Codex backend Responses and
  compact routes refuse them with a 400 naming `/v1`. `/v1/models`, `/v1/responses`, `/v1/chat/completions` and
  `/v1/messages` serve them.
- **Continuations.** Requests are sent with `store: false` and continued from codex-lb's local history through the
  stateless adapter OpenRouter, Claude and Antigravity already use. Stored responses belong to one OpenAI
  organization, so relying on them would pin a conversation to a single key and break failover after a billing
  refusal; local replay lets any eligible key serve the next turn.
- **Pooled routing.** The OpenRouter cooldown store becomes `source_cooldowns`, keyed by source and model scope,
  and account selection, cooldown checks and failure recording serve both pooled kinds. Policy lookup reads the
  kind's account table. Billing codes cool the whole account (`*`) until the next configured credit renewal, or
  six hours when no renewal day is configured. A manual refresh clears the account's cooldowns. 401, billing 429
  and rate-limit 429 refusals try another eligible account of the same kind before output is delivered.
- **Images.** `forward_native_image` resolves image redirects, then sends `openai-apikey/` image models to a new
  adapter: POST `/images/{generations|edits}` with the bare model and the unchanged JSON body. Event streams pass
  through; usage comes from the completed event or the JSON body. Settlement and request logs reuse the source
  helpers. Both Codex and `/v1` image routes reach it, including converted multipart edits.
- **Image redirects.** An image redirect's source must be a `gpt-image-*` slug and its target an enabled OpenAI API
  image model. Text redirects keep refusing image targets. OpenRouter image models keep their own request shape and
  are requested by their own slug.
- **Credit estimate.** The account stores an optional monthly credit amount and renewal day (clamped to the month's
  length). The dashboard shows the cycle, spend recorded on that source since the cycle start, the estimated
  remainder and whether a billing exhaustion is active. It is labelled an estimate: spend outside codex-lb is not
  visible.

## Risks / Trade-offs

- The estimate drifts when the same organization is used elsewhere; the exhaustion signal from OpenAI remains
  authoritative and is shown next to it.
- Registry metadata may lag new API models; such models use conservative defaults until the registry knows them.
- Renaming the cooldown table touches OpenRouter routing; existing rows are carried over by the migration.

## Migration Plan

One forward migration after `20261120_010000_index_requested_models`: create `openai_api_accounts` and rename
`openrouter_cooldowns` to `source_cooldowns`. Downgrade reverses both. No production configuration changes.
