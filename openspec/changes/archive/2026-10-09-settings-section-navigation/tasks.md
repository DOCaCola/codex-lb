## 1. Spec

- [x] 1.1 Proposal, context and spec deltas; `openspec validate settings-section-navigation --strict`.

## 2. Frontend

- [x] 2.1 Settings layout route with side menu (permission-filtered, horizontal scroller on phones) and one child route per section; `/settings` opens General.
- [x] 2.2 Move every card into its section; remove the Advanced and Organisation collapsible groups; the Organisation summary line becomes the section description.
- [x] 2.3 Automations page becomes the Automations section; remove `/automations`, `/firewall`, the full-page `/settings/access` and the header Advanced menu.
- [x] 2.4 Drop the automations row from Background jobs and the "same setting as" copy.
- [x] 2.5 Replace the deep-link helpers (Access tabs, Organisation anchors, OIDC return URL); update the step-up toast, account menu and People tab links; remove the "View full page" link.
- [x] 2.6 Route scroll restoration without the `/firewall` special case.
- [x] 2.7 Locales (en, ko, zh-CN): section and group labels, page subtitle; remove unused keys.
- [x] 2.8 Tests and browser smoke.

## 3. Backend and docs

- [x] 3.1 `OIDC_SETTINGS_PATH` = `/settings/organisation#oidc`.
- [x] 3.2 Update Settings breadcrumbs in `docs/`.

## 4. Verification

- [x] 4.1 `tsc -b`, `eslint .`, affected vitest suites, OIDC backend tests.
- [x] 4.2 Render check: light/dark, desktop/phone, read-only viewer.

Verification (2026-10-09): `tsc -b` and `eslint .` clean. Full vitest run: 1883 passed; the 5 failures (ko/zh-CN locale parity for request-log operation keys, MSW handler coverage, both `apis-page-flow` tests) predate this change. `tests/integration/test_oidc_provider_gates.py`: 35 passed. Browser smoke against a local backend: every Settings test passes (quota webhook, scroll restoration with `/settings/access#firewall`, model source dialogs); the 15 remaining failures are dashboard/account fixtures that predate this change. Render check of all ten sections at 1440 and 390 px in light and dark, and as a guest: no horizontal overflow; Organisation is unlisted for guests and redirects to General; the Model catalogue keeps "Add override"; Upstream timeouts keep their descriptions, default tags and second units; the phone menu centres the open section.
