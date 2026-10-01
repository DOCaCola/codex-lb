# Design

## Context

Account presenters already share shells and provider-specific name components.
Request logs carry account/source provenance. The dashboard model catalog provides
display names, but logs currently show raw IDs. Concurrent uncommitted consumer
cost and Claude subscription changes must remain intact.

## Goals / Non-Goals

Goals: consistent local provider identity and scan-friendly model labels.
Non-goals: changing routing, brand shapes, model IDs, filtering or provider APIs.

## Decisions

- Keep SVGs under frontend/public/images/providers; document asset provenance.
  Use official OpenAI (for Codex accounts), Claude and OpenRouter glyph paths, recolored
  black without wordmarks, metadata or external resources.
- Share a decorative provider logo and flex/truncating name wrapper. Logos use
  a fixed footprint and dark-mode inversion; private text stays separate.
- Determine log logos from source kind/native account ownership, never model
  prefixes (an OpenRouter account may serve an OpenAI or Anthropic model).
- Fetch the existing model catalog through the dashboard's query cache and pass
  names to the presentational table. Logs do not wait on that fetch. Historical
  IDs use a deterministic readable transformation, retaining exact IDs in title.
- Preserve effort/tier suffixes and operation labels; remove monospace model-cell
  styling. Keep existing detail/copy/filter IDs unchanged.

## Risks / Trade-offs

- Narrow headings: min-width zero, fixed-size marks and ellipsized name spans.
- Catalog absence: explicit historical-name formatting, no fake catalog records.
- Brand rights: marks identify providers only; source attribution is retained.

## Migration Plan

Frontend-only build; no settings, migration or production requests.
