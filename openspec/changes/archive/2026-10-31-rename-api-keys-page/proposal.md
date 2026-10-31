## Why

The dashboard page that manages downstream API keys is labelled "APIs" at `/apis`. The name reads like an API
catalogue rather than the keys clients authenticate with. The references call this page "API Keys": sub2api (`/keys`),
OmniRoute and opencodex use that label, and agent-lb uses "Keys" at `/keys`. With providers now owning keys of their
own (OpenRouter), the explicit "API Keys" label avoids ambiguity.

## What Changes

- The page moves from `/apis` to `/keys`; `/apis` is not redirected and renders the not-found surface.
- The header item and page heading read "API Keys".
- The core-destination requirement now names Providers, matching the earlier Providers rename.

## Impact

- Affected specs: `frontend-architecture`
- Affected code: `frontend/src/App.tsx`, `frontend/src/components/layout/nav-items.ts`, locale files, tests, docs
- Bookmarks to `/apis` stop resolving.
