# Design

## Context

The table already resolves names from the cached model catalog and displays
actual service tier before the recorded billing tier. A combined string formatter
cannot assign separate styling to model identity and secondary metadata.

## Goals / Non-Goals

Goal: muted inline metadata without routine default-tier noise.
Non-goals: changing request detail fields, other formatter consumers, model
filters, stored metadata, routing or pricing.

## Decisions

- Render model text and a secondary metadata span under the existing native-title
  wrapper. Use `text-muted-foreground`, not a new grey or badge style.
- Join effort/non-default tier with the established middle dot. Explicitly omit
  `default`; retain other tiers and requested-versus-actual indicators.
- Keep catalog names authoritative. The catalog provides model names and effort
  identifiers, not separate effort display labels; show recorded effort identifiers.
- Leave the shared string formatter unchanged because request details and other
  surfaces have not been requested to change.

## Risks / Trade-offs

Split text affects text-match tests: assert identity, metadata styling and full
cell content independently. Keep whitespace and native title within one truncating
line so narrower widths retain the existing table containment behavior.

## Migration Plan

Frontend-only build; no migration or new settings.
