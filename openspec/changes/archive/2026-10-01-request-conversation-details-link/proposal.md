# Request conversation details link

## Why

Request details expose a conversation ID that filters request logs, but operators
also need direct access to that conversation's existing activity details.

## What Changes

- Add a separate View details action beside the conversation ID.
- Reuse the existing Conversation Details dialog and read permission.
- Preserve conversation filtering, copying, and request-log state.

## Impact

- Frontend request-details UI and frontend-architecture specification.
- No API, storage, navigation, or permission changes.
