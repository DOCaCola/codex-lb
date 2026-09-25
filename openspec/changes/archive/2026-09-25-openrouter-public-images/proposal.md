# OpenRouter public Images API

## Why
Image-only OpenRouter models have a dedicated catalog, capability contract, pricing, and `/images` transport. Treating them as conversational models or Responses tools is incorrect.

## What Changes
Synchronize image catalogs alongside text models; enable explicit image model selections in the existing account UI. Route public image generation and multipart editing to OpenRouter, with capability validation, bounded JSON/SSE processing, usage settlement, and account restrictions. Native Codex image routes remain unchanged.

## Impact
Model search gains composable capability filters for text, images, vision, tools and reasoning.
OpenRouter account metadata, public Images routes, model discovery and dashboard model selection. No inference fallback, new credentials, or deployment.
