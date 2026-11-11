# Design: hide models from client model lists

## Client behaviour this relies on

Codex (codex-rs, models-manager): `get_model_info` resolves every catalog entry
regardless of visibility. With a `model_catalog_url` provider (our setup), lookup
is exact-slug and has no bundled fallback.

| Model state in the catalog | Client metadata | Pickers | `/model <slug>` (TUI) |
|---|---|---|---|
| `list` | full | shown | allowed |
| `hide` | full | omitted | rejected ("unavailable") |
| absent | synthetic fallback (272k, generic prompt, no efforts) | omitted | rejected |

Resuming a thread never swaps its model; `allowProviderModelFallback` exists only
for `thread/start` and is opt-in. Hidden is therefore the safe state for a retired
model, while absent degrades the thread.

Claude Code has no visibility field: its `/v1/models` list is the picker, and a
model omitted from it remains usable by name through `/v1/messages`.

## Decisions

1. **Rendering-only.** Hiding is applied where the three client lists are built
   (`_build_codex_models_response_body`, `_build_models_response_body`,
   `_build_anthropic_models_response_body`). The model registry, source catalogs,
   `list_model_catalogue()`, routing and `/api/dashboard/models` never see it. This
   keeps hidden models editable in the catalogue, selectable for compaction routes
   and API-key allowlists, and leaves `routed_base_instructions` (derived from the
   unscoped registry) unchanged.
2. **Global over per-key.** An operator-hidden slug is `hide` for every API key,
   including keys whose `apply_to_codex_model` allowlist names it. The allowlist
   decides access; the catalogue decides what pickers offer.
3. **Metadata ownership unchanged.** Hiding never changes which entry supplies a
   slug's metadata: a same-slug source entry that is operator-hidden still replaces
   retained native metadata, since the source is what routes the slug.
4. **Storage.** `hidden_models(slug PK, created_at)`; a row means hidden. No
   environment counterpart. Rows survive the model leaving the catalogue, so a
   returning model comes back hidden. The catalogue only lists current models, so
   such rows are not shown.
5. **Snapshot.** The catalog builders read hidden slugs once per build from a
   `DashboardRowsCache` invalidated through the cross-replica `settings` namespace,
   as for context-window overrides; past the TTL with the database unreachable the
   last known rows keep applying.
6. **API.** `PUT /api/settings/hidden-models/{slug}` (no body, idempotent) hides,
   `DELETE` lists again (404 `hidden_model_not_found` when not hidden). Both
   require dashboard write access, validate the slug like context-window overrides,
   reject slugs outside the catalogue with 400 `model_not_in_catalogue` (PUT only,
   so a stale row can still be deleted), return the catalogue response, and record a
   `settings_changed` audit event naming `hidden_models` and the slug.
7. **UI.** A "Client lists" switch column (Listed/Hidden), saved immediately; rows
   grouped by provider; an All/Listed/Hidden filter; hidden rows dimmed. Compaction
   route pickers keep hidden models and mark them. Mockup:
   `model-visibility-mockup.html` (variant A).

## Not covered

- Raw upstream `hide` entries (for example `codex-auto-review`) are not in the
  catalogue and cannot be listed by an operator.
- The Codex TUI cannot select a hidden model with `/model <slug>`; switching back
  needs `config.toml` or a new thread with `--model`.

