## Context

See proposal.md for motivation. The providers have separate API contracts and different quota units. Native accounts already have card/list dashboard views and a searchable master/detail Accounts page.

## Goals / Non-Goals

**Goals:** One account collection per page; consistent surfaces, typography, actions, status and privacy handling; preserved provider-specific details.

**Non-Goals:** Backend unification, routing changes, adding keys, deployment, or pretending dollar allowances are Codex subscription quotas.

## Decisions

- Compose both typed provider collections in the existing containers instead of coercing OpenRouter data into native account schemas.
- Share card and selectable-row surfaces; display dollars and key allowance for OpenRouter, keeping native quota controls unchanged.
- Integrate the provider editor into the existing add-account chooser and detail column. Keep model selection and credential forms provider-owned.
- Reuse the native Pause/Resume control rather than an enabled switch; match action sizing and destructive-delete styling without exposing native-only quota controls.
- Name sorting, search, status filtering and URL selection include both providers. Native-only quota/reset sorting puts provider accounts without the corresponding metric last.
- Fetch monitoring independently; errors must remain visible without suppressing native accounts.

## Risks / Trade-offs

- Different units → label OpenRouter values explicitly and exclude them from Codex subscription aggregate quotas.
- Stale dialog objects → resolve selected account from the live query; retain stable selection in the URL.
- Layout regressions → exercise card/list, mixed and OpenRouter-only states, read-only views, and desktop/mobile screenshots.

## Migration Plan

Frontend-only update, no database migration. Existing account IDs and API contracts remain unchanged.
