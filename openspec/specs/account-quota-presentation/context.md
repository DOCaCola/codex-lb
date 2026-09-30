# Account quota presentation context

## Luna Reserve scope

The [presentation specification](spec.md) adds current Reserve fill bars, not a
historical graph. Ordinary account quota remains the main usage display. Reserve
reuses Spark's additional-quota container, typography and percentage-used bars,
with 5h and Weekly in two columns on desktop and one column on narrow screens.

## Persistence and account binding

Reserve is conditional telemetry rather than model admission. Its latest typed
observation is retained in account metadata, not the additional-quota history or
routing registry. Writes compare the queried credential ciphertext and observation
time; re-import clears the snapshot. Conflicting account/user echoes are rejected.
The nullable column leaves historical accounts unknown until a successful refresh.

## Missing data and freshness

Availability does not imply usage. Missing percentages have no filled bar, an
absent Reserve limit removes the row, and stale observations show unknown usage
without current windows. Freshness follows the existing usage horizon rather than
a Reserve-only setting. A relative reset deadline is anchored to the observation
time so rereading a snapshot cannot extend its countdown.

For example, a response reporting primary usage 25% over 18,000 seconds and
secondary usage 60% over 604,800 seconds renders `5h: 25% used` and
`Weekly: 60% used`. It does not contribute to ordinary quota totals or authorize
clients to use a Reserve model.

## Upstream references and operational qualification

Inspected 2026-09-30:

- OpenAI Codex `60947e234156ac12bdb7fba2477d3965f166bd34`, usage client,
  generated rate-limit parser and Luna Reserve UI tests: the query capability is
  `x-openai-codex-luna-reserve: 1`, and `gpt-reserve` has primary/secondary windows.
- OpenCodex `cae9b553e9b882dd13781a7f3ee6f68c0dcc8c4f`,
  `src/codex/reserve-availability.ts`: fresh credential-bound inference eligibility
  is a separate concern, not permission granted by this display.

Account refresh explicitly opts into the capability for operator telemetry;
passive reset-credit reads do not. Mocked API/browser tests qualify parsing and
presentation only. No live Reserve-bearing response was available to establish
account entitlement. Deployment requires the nullable account snapshot migration.
