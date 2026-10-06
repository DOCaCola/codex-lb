# Logs Tab

## Why

The dashboard stacked the request logs and conversations views beneath the overview, quota and account sections. They
were only reachable by scrolling past the overview, and the switch between them was a small dropdown inside the section
heading. That control was easy to miss. Both views share the overview's account data but none of its charts, so a
separate page fits them better.

## What Changes

- A new core navigation destination, Logs (`/logs`), sits second in the header after Dashboard. It requires
  `dashboard:read`.
- The Logs page hosts the request logs and conversations views with their existing filters, column layout, URL
  parameters and permission rules.
- A segmented toggle switches between Request Logs and Conversations. It uses the same style as the dashboard's
  Codex/Claude quota switch.
- The dashboard no longer renders request logs or conversations. Its stat boxes always follow the overview timeframe;
  they no longer follow the conversation timeframe.
- The core navigation budget rises from five to six items.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-architecture`: header navigation includes Logs; request logs and conversations move to the Logs page.

## Impact

- Frontend only: `features/logs`, the dashboard page, navigation, routes and locales.
- Links to `/dashboard?view=conversations` now open the dashboard; conversations are at `/logs?view=conversations`.
