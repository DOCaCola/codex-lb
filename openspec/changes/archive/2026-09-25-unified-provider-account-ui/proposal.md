## Why

OpenRouter accounts currently occupy separate dashboard and Accounts sections, fragmenting account management and using a different visual language from Codex accounts.

## What Changes

- Show both providers in the existing dashboard account cards and list.
- Include OpenRouter in the existing searchable Accounts list and add-account chooser, with provider-specific details in the shared detail column.
- Preserve distinct credit, allowance and quota semantics, monitoring freshness, permissions and provider controls.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `openrouter-accounts`: Unified provider presentation on the dashboard and Accounts page.

## Impact

Frontend account/dashboard composition, OpenRouter presentation, UI tests and operator documentation. No backend contract, credential, routing or production configuration changes.
