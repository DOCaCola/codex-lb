# Context: settings section navigation

## Purpose

Give every setting one predictable address. The side menu answers "where is X"
without expanding anything, and a link can point at a section or a card.

## Placement (section → cards, in order)

| Group | Section | Cards |
|---|---|---|
| Workspace | General | Appearance |
| Workspace | Accounts | Import, Reset credits, Background jobs (Auth Guardian, reset-credit polling) |
| Workspace | Access | Access (People / My sign-in), API keys, Firewall |
| Workspace | Organisation (`security:write`) | Company sign-in, Reverse-proxy sign-in, Sign-in rules, Password sign-in, Automatic account management |
| Traffic | Routing | Routing, Quota planner, Sticky sessions, Cross-account cache isolation probe |
| Traffic | Models | Model catalogue |
| Traffic | Upstream | Upstream proxy routing, Resilience, Session bridge, Upstream timeouts |
| Operations | Automations | Pause all automations, Jobs, Recent runs |
| Operations | Data | Data retention, Conversation archive |
| Operations | Notifications | Quota reset webhook |

Each card keeps its existing permission rule (for example API keys and sticky
sessions need `write`, the probe needs `ops:write`, the Access card needs `write`
or a personal sign-in). Only Organisation is hidden from the menu, because every
card in it needs `security:write`; every other section has at least one card a
read-only viewer can see.

## Decisions

- **Routes, not tabs.** Each section is a child route of the Settings layout, so
  the browser history, the address bar and links work per section, and a section's
  queries run only when it is open. That keeps the "collapsed sections do not
  fetch" property the old groups existed for.
- **No compatibility redirects.** The fork has one deployment; old bookmarks land
  on the not-found surface. The OIDC return path is the only server-chosen URL
  and moves in the same change.
- **The automations scheduler has one switch.** "Pause all automations" carries
  the paused badge, the inverse-wording caption and the provenance badge; the
  duplicate row in Background jobs is dropped rather than kept in sync.
- **Data stays where the card needs it.** The layout owns the settings query, the
  save mutation and the notices; the Routing section owns the account lists, and
  the Upstream section owns the upstream-proxy admin query and its mutations.

## Example

An administrator follows the "Confirmation not possible" toast after a refused
step-up: it opens `/settings/access#my-sign-in`, the Access card selects My
sign-in, and the TOTP card is a scroll away. A completed company sign-in test
returns to `/settings/organisation#oidc` and scrolls to the Company sign-in card
once the Organisation queries have loaded.

## Pending upstream changes

Several unarchived upstream changes (`access-settings-card`,
`role-mappings-and-organization-group`, `oidc-connect-wizard`,
`local-login-policy-and-break-glass`, `login-and-header-tiering`,
`enable-operator-viewer-presets`, `retire-legacy-credential-mirror`,
`auth-provider-abstraction`, `step-up-auth`) describe the superseded addresses
(`/settings#access`, `/settings#organisation`, `/settings?org=1#oidc`, the
full-page `/settings/access`). This change's requirements are the current
contract for those addresses in the fork.
