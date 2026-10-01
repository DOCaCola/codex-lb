# Standard operation label presentation

## Scope and rationale

Ordinary Responses and Messages traffic needs no repeated subtitle. Suppression
belongs in the shared table formatter, not server classification or provider
selection. The retained operation remains useful in details and API metadata.

## Examples and boundaries

Normal Responses or Messages: no subtitle or empty margin.
Responses Warmup and Messages Prewarm: Warmup and Prewarm alone.
Compaction and Checkpoint handoff: explicit labels, including operations arriving
through Responses. Claude via Codex remains Responses; no model-based guessing.
Historical unknown operation labels and other special operations remain visible.

## Verification

- 183 formatter, schema and request-table tests passed, including details retention,
  no empty secondary line, workload-only labels and all nonstandard operations.
- Two built-dashboard browser tests passed at 390px and 1440px, checking special
  labels, absent standard labels, table columns and page containment.
- Frontend type checking, production build and changed-file ESLint passed.
- Strict change validation and all 75 main specs passed; diff whitespace clean.

Main spec/context are synced. No API/backend/migration changes are included.
Archiving, committing, pushing and deployment were subsequently authorized.
