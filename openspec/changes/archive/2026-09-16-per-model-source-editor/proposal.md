## Why
Shared model fields make it impossible to manage heterogeneous models safely. Operators need individual names, limits, capabilities and prices.

## What Changes
- Separate connection settings from an individually selected model editor in create and edit dialogs.
- Support adding, removing and enabling models, preserving unedited metadata.
- Validate numeric values and duplicate IDs, distinguish unknown pricing from free.

## Impact
Frontend only; existing model-source API and pricing contracts remain unchanged.
