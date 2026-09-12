# Native Codex image forwarding

## Why
Codex's ChatGPT-authenticated image extension calls native JSON Images endpoints. Translating these requests to Luna Responses tool calls changes upstream behavior and loses native errors and metadata.

## What Changes
- Forward Codex-base image generation and edit JSON to the selected ChatGPT account's native image endpoint.
- Preserve native status, body and safe response metadata; never replay an image operation after dispatch or fall back to a model source.
- Retain account scope, admission, API-key policy, tracked reservation cleanup and bounded observability.
- Leave public `/v1/images/*` adapter behavior unchanged.

## Impact
Proxy image routes, unary transport/account lifecycle, Images specifications and regression tests. No deployment or live generation is part of verification.
