## Why

Every top-level page renders its title differently:

- Dashboard: a small title with the health line and refresh button.
- Reports: a small title inside the sticky toolbar card, divided from the range presets.
- Logs: no title.
- API Keys and Providers: a medium title with a summary and actions.
- Settings: a large title with an icon and a subtitle below it.

## What Changes

- One shared title row for Dashboard, Logs, Reports, Providers, API Keys and Settings: a medium title, optional muted
  context next to it, actions on the right, above the content and outside any card.
- Logs and Reports move their first toolbar row (view switch or range presets, refresh, summary, pager) into the title
  row, so the title adds no height; their filters stay in a card below. Reports keeps the title row and filter card
  pinned together. Settings drops its icon and subtitle.
- Detail views keep their breadcrumb.

## Capabilities

### Modified Capabilities

- `frontend-architecture`: page title presentation on the top-level pages.
