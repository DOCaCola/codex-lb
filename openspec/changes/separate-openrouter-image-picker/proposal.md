# Separate OpenRouter image selection

## Why
Image endpoints need their own discovery surface instead of being buried among conversational models.

## What Changes
Add an Image models action and scoped picker alongside Models, retaining one provider selection list and preserving hidden selections on save.

## Capabilities
### New Capabilities
- `openrouter-image-selection`: scoped image and general model selection.

## Impact
Dashboard controls and tests only; no migration, backend routing change or production configuration change.
