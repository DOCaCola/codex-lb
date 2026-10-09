## Why

Settings has grown into one long page: a handful of core cards, an "Advanced
settings" collapsible holding fourteen more, an "Organisation" collapsible at
the bottom, and three related surfaces elsewhere (`/automations` behind a header
"Advanced" menu, `/settings/access` as a full-page People table, `/firewall` as a
redirect into the collapsible). Operators have to know which group hides a card,
and the automations scheduler switch exists twice (Background jobs and the
Automations page).

## What Changes

- **BREAKING** Settings becomes a layout with a side menu of ten sections, each
  its own route under `/settings/<section>`, grouped as Workspace (General,
  Accounts, Access, Organisation), Traffic (Routing, Models, Upstream) and
  Operations (Automations, Data, Notifications). `/settings` opens General. Every
  existing card moves unchanged into exactly one section; no setting is added or
  removed.
- Remove the "Advanced settings" and "Organisation" collapsible groups. A section
  only mounts (and fetches) when it is opened, which replaces the collapsed-group
  rule. The Organisation summary line becomes that section's description.
- **BREAKING** Automations moves into Settings → Automations. The header
  "Advanced" menu (desktop and mobile) is removed; the header shows the core
  destinations only. The "Automations scheduler" row leaves Background jobs: the
  "Pause all automations" control on the Automations section is its one home.
- **BREAKING** No legacy redirects: `/automations` and `/firewall` stop
  resolving, `?advanced=1`, `?org=1` and the `#firewall`/`#access`/
  `#access-people`/`#organisation` deep links are retired. `/settings/access` is
  the Access section (it no longer renders the People table on its own; the card's
  "View full page" link goes away because the section already has the width).
- New deep links: `/settings/access#people`, `/settings/access#my-sign-in`,
  `/settings/access#totp`, `/settings/organisation#oidc`,
  `#organisation-login-policy`, `#organisation-automatic-accounts` and
  `#organisation-refused`. The OIDC flow returns to `/settings/organisation#oidc`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-architecture`: Settings page structure, header navigation, the
  Automations destination, the retired `/firewall` route and the route-scroll
  rule for hashed destinations.
- `automations`: the pause control has one dashboard home.
- `rate-limit-reset-credits`: the polling switch's dashboard location.

## Impact

- Frontend: `App.tsx`, header and nav items, the Settings page (split into a
  layout and section pages), the Automations page (becomes a section), Access
  card/People tab, Organisation group, deep-link helpers, step-up toast, account
  menu, OIDC return URL, route scroll restoration, locales, tests and browser smoke.
- Backend: `OIDC_SETTINGS_PATH` in `app/modules/dashboard_auth/oidc_api.py`.
- Docs: Settings breadcrumbs in `docs/`.
- Upstream merges: conflicts in the Settings page, header and deep-link files
  resolve by keeping the section layout and placing new cards in a section.
