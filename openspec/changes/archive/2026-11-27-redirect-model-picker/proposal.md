## Why

The image redirect target `openai-apikey/gpt-image-2.6-sunburst` was offered by the settings API but could not be
chosen. The requested-model field never suggested `gpt-image-2`, the model Codex clients send to the image backend;
image targets appeared only after typing an image model name; and image targets were mixed into the requested-model
suggestions. Provider models that are not yet enabled could not be redirected to at all without enabling them first.

## What Changes

- `GET /api/settings/model-redirects` additionally returns `imageSources`, the image models clients request
  (`gpt-image-2`), and `disabledModels`, the text models each connected provider offers but does not publish.
- Both redirect fields use a shared searchable model picker. The requested-model picker lists client requests in
  their own highlighted section, separate from provider catalogues, accepts any typed slug, and offers a
  "Show disabled models" switch. The served-model picker opens only after a requested model is chosen and lists
  image targets for image sources and text targets otherwise.

## Capabilities

### Modified Capabilities
- `model-catalog-compat`: the redirect settings response lists client image sources and unpublished provider models.
- `frontend-architecture`: the Redirects card uses the sectioned, searchable model picker.

## Impact

`app/modules/settings`, the provider catalog modules (Claude, Antigravity, OpenRouter, OpenAI API), the new
`frontend/src/components/model-picker.tsx` and the redirect settings form. No routing or stored-data change.
