# Context: frontend-architecture

Normative requirements live in [`spec.md`](./spec.md). This document currently
covers the progressive-disclosure navigation, settings and shared dashboard presentation.

## Dashboard provider card presentation

Codex, Claude and OpenRouter card presenters supply identity/status, provider content and actions to one shared shell. It owns header typography and space for an optional identity description, body spacing, notice styling and the bottom action footer. Quota windows share a card-specific grid for Codex and Claude; provider units and unknown/stale states remain distinct. Details/list surfaces retain their existing layout.

All card types receive the same flexible animation wrapper. At multi-column breakpoints, intrinsic equal-height grid rows size themselves from the tallest rendered content; no fixed row height, viewport cap or card scrollbar is used. A Claude-only last row therefore matches the preceding Codex row without fake credit or warm-up fields. Single-column mobile uses natural heights instead of padding every sparse card to the tallest one. Long action groups can wrap and increase the required content height safely.

For example, a Codex alias with an email subtitle, a plain Codex identity and an OpenRouter balance card align at their body start and footer despite different content. Mobile Codex/Claude cards with two windows both keep two quota columns. Browser tests measure bounds and containment in light/dark themes at 1440, 768, 390 and 320 pixels.

Dashboard card subtitles keep concise provider/plan identity: `Plus`,
`OpenRouter · Paid`, and `Claude · Pro` when Claude subscription discovery
provides a plan. Optional Codex account IDs also use `·`.
Model counts and `All models` belong in account selection controls, not these
overview cards. Account actions, privacy and the common card shell are unchanged.

## Provider identity and readable request models

Local text-free SVG marks live under `frontend/public/images/providers/` and
identify the account provider rather than the model vendor. A shared 16-pixel
decorative mark/name wrapper preserves existing privacy, truncation and actions;
black marks invert in dark mode. An OpenRouter account serving GPT 6 Astra still
shows the OpenRouter mark. Codex accounts use the OpenAI knot at the operator's
request; application-level Codex branding is unchanged.

Sources inspected 2026-10-01: the OpenAI knot from the inline SVG served by
https://openai.com/ (including its JavaScript/cookie challenge page); the Claude
sunburst from https://claude.com/; the OpenRouter glyph from
https://openrouter.ai/brand/v2/openrouter-glyph-light.svg. Original glyph geometry
is retained, wordmarks omitted and fills recolored black. The OpenRouter viewBox
matches the trimmed glyph bounds used inline on its website. SVGs include no
scripts, fonts or external resources; viewing the dashboard fetches only local
assets. Marks identify providers, not endorsements.

Request-log model cells use the existing cached catalog's names. Historical IDs
not present in the catalog receive readable formatting without changing stored
IDs, filters, detail or copy values. For example,
`anthropic/claude-haiku-4-5-20251001` displays `Claude Haiku 4.5`, with the full ID
in the native browser title. Catalog loading does not block request logs, and
reasoning/service-tier suffixes and operation labels remain intact. Unknown
account provenance receives no speculative provider logo.

Browser regressions verify local asset safety, light/dark contrast, account
cards/lists/logs/details and document containment at 320, 390 and 1440 pixels.
No backend contract, configuration, migration or routing changes are required.

## Weekly pace consumer costs

The weekly runway's top consumers use a trailing two-hour attribution window,
independent of the overview timeframe selector. Their estimated API costs use
that exact request-log filter and sum recorded costs across every model, not a
conversion of weekly quota credits. Shared request-level coverage rules exclude
non-billable local refusals and token-count operations; attribution excludes
warmup probes, deleted rows and requests outside the window.

For example, two priced requests costing $1 and $2 plus an unpriced metered
request display `$3.00`, with partial coverage explained in the tooltip. No
known prices display `Unknown`; explicitly free metered requests display `$0.00`.
The inline amounts deliberately omit coverage counts and lower-bound symbols.

The existing grouped attribution query carries typed coverage alongside usage;
there is no per-consumer fetch and consumer ranking remains unchanged. Candidate
deduplication keeps the per-key total instead of summing it twice when a key
ranks by both requests and tokens. The model label shares the consumer-name
cell, and container queries wrap metrics in narrow cards, including desktop
side columns. Browser regressions cover 320, 390 and 1440-pixel viewports.
Backend and frontend must be updated together for the required coverage field;
there is no database migration or new pricing setting.

## Progressive disclosure (nav + settings)

### Purpose

Part of the simplicity effort (PRINCIPLES.md P3, progressive disclosure): keep
the first-run dashboard surface small — import accounts, hand out an API key,
point a client at the proxy — while every power feature stays one explicit
interaction away.

### Decisions

- **Core vs Advanced split.** Nav: Dashboard, Reports, Accounts, APIs,
  Settings are core; Automations (scheduled warm-up jobs) is the only advanced
  destination today. Settings: Appearance, Import, Guest Access, Password,
  Session, TOTP, and API Keys stay flat; Routing tuning, Upstream Proxy pools,
  Model Sources, Firewall, Quota Planner, and Sticky Sessions collapse into
  the Advanced group.
- **One-item Advanced menu is intentional, not over-engineering.** The menu is
  the mandated landing zone for future power features per PRINCIPLES.md P3: a
  new page-level destination defaults to the Advanced menu unless a spec
  explicitly designates it core.
- **Advanced sections fetch on expand, not on page load — intentional.** The
  Advanced settings group unmounts its children while collapsed (Radix
  Collapsible default, no `forceMount`). Sections that issue queries on mount
  (firewall entries, quota planner, sticky sessions, model sources) therefore
  do not fire network requests when an operator merely opens `/settings`; the
  requests fire on the first expand. This trims first-paint work for the
  common path and must not be flagged as a data-loading regression.
- **Arrays stay in `app-header.tsx`.** `CORE_NAV_ITEMS` and
  `ADVANCED_NAV_ITEMS` are flat `as const` arrays in the header component (no
  separate nav-items module); the CI simplicity budget manifest
  (`.github/simplicity-budgets.toml`, `[core_nav]`) points at this file.
- **No new routes.** `/automations` deep links stay as-is. The legacy
  `/firewall` compatibility route redirects to `/settings?advanced=1#firewall`
  so Advanced expands and the firewall section is in view; plain `/settings`
  stays collapsed by default. Regression tests cover both.

### Example

A read-only guest opens `/settings`: they see Appearance, Import, and API Keys
cards plus a collapsed "Advanced settings" row. No firewall/quota/sticky-session
requests have been issued. One click on the row mounts all six advanced
sections with their controls disabled by the existing `canWrite` gating.

### Testing notes

- Tests that asserted advanced sections on load (settings-page unit test,
  firewall integration flow, header Automations link) expand/open first —
  asserting through the same one-interaction path an operator uses.
- The accounts reset-credits badge stays on the core Accounts item in both
  desktop and mobile navs.

## Direct conversation details from request details

Request details expose two distinct actions: the conversation ID retains its
existing request-log filtering behavior, while the adjacent Details link opens
the same Conversation Details dialog used by the Conversations view. Both reuse
the existing `conversations:read` gate. The details dialog is mounted only after
selection, so viewing request metadata alone does not issue a conversation query.

For example, an operator inspecting a request from `conv / a` can open that
conversation's activity and model breakdown without leaving a filtered request
list or resetting its page. The existing query encodes the opaque ID and owns
loading/error handling; closing the dialog clears the local selection. No new
route, permission, API, or conversation storage is introduced.

## Dashboard partial-failure isolation

### Purpose and scope

The dashboard overview and request-log listing are independent operator surfaces. A request-log storage or listing outage should not remove healthy fleet quota and account controls. Normative behavior lives in [`spec.md`](./spec.md); while the change is active, its added requirement lives in [`../../changes/preserve-dashboard-overview-on-log-failure/specs/frontend-architecture/spec.md`](../../changes/preserve-dashboard-overview-on-log-failure/specs/frontend-architecture/spec.md).

### Decision rationale

The page composes overview-backed view data as soon as overview data exists and treats request logs as a section-local state machine: initial loading, terminal error announced through a local alert semantic, or ready. Recovery calls the existing request-log query's local refetch operation. A broader dashboard invalidation was rejected because it would refetch healthy data and could make usable incident context disappear.

### Constraints and non-goals

This boundary does not change API shapes, query keys, retry policy, polling, or backend reliability. It does not preserve stale rows after later refetch failures, introduce route splitting or global state, or define global live-region behavior. The header refresh action intentionally keeps its existing broad refresh semantics; only the Request Logs Retry action is local.

### Failure mode and example

If overview, projections, and request-log options return successfully while the initial listing reaches terminal HTTP 500, operators continue to see statistics, quota charts, and account controls. The Request Logs heading remains visible with a locally announced endpoint error and native Retry control. After the endpoint recovers, keyboard-activating Retry replaces that error with the returned rows without issuing another overview request.

### Testing notes

The product-boundary regression renders the real `/dashboard` App route with the production query retry policy and MSW handlers. It counts each request family, seeds unique values for a statistic, quota surface, projection metric, and account control, focuses and keyboard-activates native Retry, holds the recovered listing response pending long enough to assert all healthy surfaces remain mounted, and then verifies the recovered row.
