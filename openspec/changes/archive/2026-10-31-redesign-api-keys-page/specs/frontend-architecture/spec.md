## MODIFIED Requirements

### Requirement: API key overview SHALL show lifetime usage aggregates

The API Keys page SHALL present the API key list `usageSummary` values as lifetime aggregates (all non-warmup
request-log history), unless the backend contract is changed to provide a bounded window explicitly. The header
summary SHALL show the lifetime cost of all keys, each table row SHALL show its key's lifetime cost, share of the
lifetime cost of all keys and request count, and a key's Overview tab SHALL show its lifetime requests, tokens and
cost with that share.

#### Scenario: Overview usage labels reflect lifetime scope

- **WHEN** the page renders `usageSummary` values for request count, token count, and cost
- **THEN** those values are labeled as lifetime usage, not as 7-day totals

#### Scenario: Lifetime share of all keys

- **WHEN** two keys have lifetime costs of $30 and $10
- **THEN** their rows show shares of 75% and 25%

### Requirement: Dashboard API-key forms assign model sources

The API-key create dialog and a key's Settings tab SHALL allow operators to assign zero or more model sources
separately from account assignments. Selecting no model sources SHALL mean all eligible sources are allowed subject to
model allowlists and route compatibility. When a source-scoped key's assigned sources were all deleted, the Settings
tab SHALL explain the missing restriction and SHALL send an empty source list only when the operator explicitly
removes the restriction.

#### Scenario: Create key scoped to a model source

- **WHEN** an operator creates an API key and selects model source `src_vllm`
- **THEN** the dashboard sends `assignedSourceIds=["src_vllm"]`
- **AND** the API key response preserves the assigned source id

#### Scenario: Edit key clears source scope

- **WHEN** an API key has assigned source ids
- **AND** an operator clears the source selection in the key's Settings tab and saves
- **THEN** the dashboard sends `assignedSourceIds=[]`

#### Scenario: Deleted sources keep the key denied

- **WHEN** a source-scoped key has no remaining assigned sources
- **AND** the operator saves its Settings tab without removing the restriction
- **THEN** the dashboard does not send `assignedSourceIds`

### Requirement: First-run empty lists describe setup, not filter mismatch

Providers, API Keys, and dashboard request-log empty states SHALL distinguish a
first-run empty source list from a filtered-empty result. When the source
list has no items and no narrowing filter is applied, the empty copy SHALL
describe setup (no accounts yet, no API keys yet, no requests yet) and SHALL
NOT tell the operator to adjust filters. When the source list has items, or
request-log filters differ from their defaults, and the visible result is
empty, the empty copy SHALL describe a filter mismatch.

#### Scenario: Accounts first-run empty copy

- **GIVEN** the Providers page has no accounts
- **WHEN** the account list renders
- **THEN** the empty title describes that there are no accounts yet
- **AND** the empty description does not tell the operator to adjust filters

#### Scenario: Accounts filtered empty copy

- **GIVEN** the Providers page has at least one account
- **AND** the current search or status filter matches none of them
- **WHEN** the account list renders
- **THEN** the empty title describes that no accounts match
- **AND** the empty description tells the operator to adjust filters

#### Scenario: APIs first-run empty copy

- **GIVEN** the API Keys page has no API keys
- **WHEN** the API key table renders
- **THEN** the empty title describes that there are no API keys yet
- **AND** the empty description does not tell the operator to adjust filters

#### Scenario: API keys filtered empty copy

- **GIVEN** the API Keys page has at least one key
- **AND** the current search or filter matches none of them
- **WHEN** the API key table renders
- **THEN** the empty title describes that no API keys match

#### Scenario: Request logs first-run empty copy

- **GIVEN** the request-log listing has no rows
- **AND** request-log filters are at their defaults
- **WHEN** the recent-requests table renders
- **THEN** the empty title is `No requests yet`
- **AND** the empty description does not say that request logs match the current filters

#### Scenario: Request logs filtered empty copy

- **GIVEN** the request-log listing has no rows
- **AND** at least one request-log filter differs from its default
- **WHEN** the recent-requests table renders
- **THEN** the empty copy describes that no request logs match the current filters

## ADDED Requirements

### Requirement: API Keys table

`/keys` SHALL show a header with the page title, the number of keys, the number of active keys, the 7-day cost and
the lifetime cost of all keys, and a Create key action for operators who may write. Below it SHALL follow the API-key
comparison chart and one table of all keys. Each row SHALL show the key's name, prefix and scope (models, accounts and
a non-foreground traffic class), its status, its first two limit meters with "+N more" for further rules, its last 7
days (a sparkline, cost and tokens from the comparison trends), its lifetime cost, share and requests, its last use,
and a menu with Open, Open in Logs, Copy prefix and, for operators who may write, Regenerate and Disable or Enable.
Activating a row SHALL open `/keys/:keyId`. The table SHALL offer search by name or prefix, an All / Active / Needs
attention / Disabled & expired filter with counts, and sorting by last used, 7-day cost, lifetime cost, name or expiry.

A key's status SHALL be Disabled when it is inactive, Expired when its expiry has passed, Limit reached when any limit
rule's current value has reached its maximum, Expiring when it expires within 14 days, and Active otherwise. Needs
attention SHALL contain Limit reached and Expiring keys; Active SHALL contain Active and Expiring keys.

#### Scenario: Limit reached

- **WHEN** an active key has a weekly cost rule at 150 of 150
- **THEN** its row shows Limit reached
- **AND** the Needs attention filter includes it

#### Scenario: Open a key

- **WHEN** an operator activates a key's row
- **THEN** the page navigates to `/keys/<keyId>`

#### Scenario: Read-only sessions

- **WHEN** a session that may read but not write keys opens `/keys`
- **THEN** the Create key action and the row menu's Regenerate and Disable entries are absent

### Requirement: API key page

`/keys/:keyId` SHALL show the key in the frame of a provider account page: a sticky, collapsible rail of all keys with
search and arrow-key navigation, a breadcrumb that becomes a key switcher on narrow screens, a header with the key's
name, status, prefix, creation, last use and expiry, the actions Open in Logs, Regenerate and Disable or Enable, and a
⋯ menu with Copy prefix, Copy key ID and Delete. A banner SHALL explain a Limit reached, Expiring, Disabled or Expired
key with a matching action. Overview and Settings tabs SHALL be addressed by `/keys/:keyId` and
`/keys/:keyId/settings`, and the rail and switcher SHALL keep the open tab. An unknown ID SHALL show "API key not
found" with a link to all keys. Read-only sessions SHALL see no write actions and no Settings tab.

#### Scenario: Switch keys on the Settings tab

- **WHEN** an operator on `/keys/a/settings` selects key `b` in the rail
- **THEN** the page shows `/keys/b/settings`

#### Scenario: Unknown key

- **WHEN** a user opens `/keys/missing`
- **THEN** the page shows "API key not found"

### Requirement: API key Overview tab

The Overview tab SHALL show a Last 7 days card with the key's requests, tokens with cached tokens, estimated cost and
last use, and one chart that shows cost and tokens together with a Per hour / Cumulative control. Beside it SHALL
follow cards for cost by account over the last 7 days as bars with provider logos and account colours, the key's limits
with current value, maximum, percentage and reset time, the pooled 5h and weekly capacity remaining when available,
the access rules in force, and lifetime usage. Edit links on the Limits and Access cards SHALL open the Settings tab
for operators who may write. Deleted accounts SHALL be labeled "Deleted Account", unattributed usage "Unknown Account",
and account names SHALL follow the privacy setting.

#### Scenario: Cost and tokens in one chart

- **WHEN** a key has hourly usage in the last 7 days
- **THEN** its Overview chart shows cost and tokens together
- **AND** Cumulative shows both as running totals

### Requirement: API key Settings tab

The Settings tab SHALL hold every field of the former edit dialog as full-width cards: General (name, expiry, traffic
class), Models and reasoning (allowed models, apply to Codex /model, enforced model, allowed efforts, enforced effort,
enforced service tier), Routing (assigned accounts, assigned model sources, HTTP client routing), Limits (rule editor,
each rule's current usage and a Reset usage action that confirms before sending `resetUsage`), and Client usage display
(usage sections), followed by a card with Regenerate, Disable or Enable, and Delete. One save bar SHALL show the
number of unsaved changes with Discard and Save changes, and SHALL send only the changed fields. Settings › Access SHALL
open a key's Settings tab to edit it.

An account-scoped key whose assigned accounts were all deleted stays scoped and can use no account. The Settings tab
SHALL explain this and SHALL send an empty account list only when the operator explicitly removes the restriction;
saving unrelated changes SHALL NOT broaden the key to every account.

#### Scenario: Save one change

- **WHEN** an operator renames a key and saves
- **THEN** the save bar disappears and the key shows the new name

#### Scenario: Deleted accounts keep the key denied

- **WHEN** an account-scoped key has no remaining assigned accounts
- **AND** the operator renames it and saves without removing the restriction
- **THEN** the dashboard does not send `assignedAccountIds`

#### Scenario: Explicitly remove a dead account scope

- **WHEN** an account-scoped key has no remaining assigned accounts
- **AND** the operator checks "Remove account restriction" and saves
- **THEN** the dashboard sends `assignedAccountIds=[]`

#### Scenario: Discard

- **WHEN** an operator changes a field and selects Discard
- **THEN** every field shows its saved value again

## REMOVED Requirements

### Requirement: API sidebar shows pooled credit bars

**Reason**: The key sidebar is replaced by the keys table and rail; pooled capacity is shown on the key's Overview tab.
**Migration**: None.

### Requirement: APIs tab shows a 7-day account-cost donut for selected API keys

**Reason**: Cost by account is shown as bars on the key's Overview tab.
**Migration**: None.

### Requirement: APIs tab account-cost donut uses existing account labels and privacy rules

**Reason**: The donut is removed; the bars keep the labels and privacy rules (see API key Overview tab).
**Migration**: None.

### Requirement: APIs tab account-cost donut follows the dashboard donut visual system

**Reason**: The donut is removed.
**Migration**: None.

### Requirement: APIs tab usage trend control layout is compact in the split view

**Reason**: The split view is removed; the key's Last 7 days card replaces it.
**Migration**: None.

### Requirement: API key edit dialog

**Reason**: Keys are edited on their Settings tab.
**Migration**: Settings › Access opens `/keys/<keyId>/settings`.
