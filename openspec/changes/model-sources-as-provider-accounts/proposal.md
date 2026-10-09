# Proposal

## Why

Settings → Models listed every model source row, including the rows that back
Claude and OpenRouter accounts. Deleting such a row through the model-source
API cascaded to the provider account. User-defined OpenAI-compatible endpoints
are upstream providers like OpenRouter and Claude, so they belong with the
accounts rather than in Settings.

## What Changes

- Remove the Model sources card from Settings → Models; the section keeps the
  model catalogue.
- Manage user-defined OpenAI-compatible sources on the Accounts page: an
  "OpenAI-compatible" group in the add-account chooser, list entries with a
  provider icon, and a detail panel with usage trends, models with pricing,
  connection details, rename, colour, Pause/Resume, Edit and Delete.
- `openai_compatible` becomes a provider identity for account colours, request
  log attribution and provider marks.
- The model-source API refuses update and delete for provider-backed rows
  (Claude, OpenRouter) and serves per-source activity trends.

## Capabilities

Modified: model-source-routing, openrouter-accounts (shared account chooser).
