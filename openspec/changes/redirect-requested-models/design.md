# Design: redirect requested models

## References

| Reference | Scope | Catalog | Response `model` | Logging |
|---|---|---|---|---|
| CLIProxyAPI `oauth-model-alias` | per provider channel, per credential | alias listed; `fork: true` also keeps the upstream id; optional `display-name` | upstream id unless `force-mapping: true` | standard |
| agent-lb `model_aliases` | global | alias visible unless excluded | served | `requested_model_alias` column; rewrite logged at warning and announced with `x-agent-lb-model-rewritten: from->to` (a59ade9) |
| sub2api `model_mapping` | per account, wildcards; doubles as allow-list; separate `compact_model_mapping` | mapped names | served | standard |
| OmniRoute | global exact and wildcard aliases; combos with fallback | aliases listed | served | standard |
| opencodex | provider `modelAliases`; combos | aliases listed | served | standard |
| upstream codex-lb, Frozen811 | built-in suffix aliases only; per-key `enforced_model` | - | - | - |

We follow the shared core (exact global mapping applied before routing, both names logged) and agent-lb's
request-log column. Per-account mappings and wildcard patterns are left out (see Not covered).

## Client behaviour this relies on

- **Codex picks request shape from the catalog entry of the slug it requests.** Context window,
  effort levels, input modalities, Responses Lite, tool formats and base instructions come from that
  entry (`model_catalog_url` lookup is exact-slug, no bundled fallback). The redirect source must
  therefore carry the served model's metadata; otherwise Codex builds a request for one model and
  another answers it.
- **Codex warns on a differing `OpenAI-Model` response header.** `maybe_warn_on_server_model_mismatch`
  (`codex-rs/core/src/session/mod.rs`) compares the header with the requested slug and, when they differ,
  emits `ModelReroute` and the warning "Your account was flagged for potentially high-risk cyber
  activity...". codex-lb never forwards that header today: the WebSocket handshake is accepted before
  upstream connects and carries only turn-state headers, and HTTP streams build their own headers. This
  must stay true for redirected requests.
- Codex does not compare the `model` field in response bodies with the requested slug.
- Claude Code lists `/v1/models` (Anthropic shape) and sends any listed or configured id to
  `/v1/messages`; it has no mismatch check.

## Decisions

1. **One resolution order.** For every request on a covered surface:
   suffix-alias normalization (`normalize_upstream_model_alias`), then API-key `enforced_model`, then
   the redirect, then the compaction route of the resolved model, then effort policy and
   unsupported-effort normalization. A single resolver returns `(requested_model, model)` where
   `requested_model` is the model after key enforcement and `model` is the served model. It replaces
   `effective_model_for_api_key`, `_effective_model_for_api_key`, `_effective_optional_model_for_api_key`
   and the inline `api_key.enforced_model` reads in `service.py`, `codex_control.py`, `warmup.py`
   (client prewarm only) and the model-list builders. Claude and Antigravity routing guards compare
   against the resolution instead of re-reading `enforced_model`; today they reject any model that
   differs from `enforced_model`, which a redirected enforced model would trip.
2. **Exact, global, single hop.** A redirect maps one slug to one slug for every API key. The target
   must not itself be a redirect source, so resolution never chains. Wildcards are out of scope.
3. **Source is any slug; target must be in the catalogue.** The main case is a model that left the
   upstream catalog, so the source need not exist. The target must be a catalogue model servable for
   text generation (native, Claude, Antigravity or model-source). A source may also be a current
   catalogue model; the redirect then overrides it.
4. **Target leaves the catalogue: fail explicitly.** Requests on the source get 400
   `model_redirect_target_unavailable` naming both models; the settings API lists the redirect as
   `inactive` with that reason; client catalogs omit the source. A redirect is also inactive when its
   target is itself redirected. Removing a redirect restores the source's registry entry when available.
5. **Catalog rendering.** While active, the source slug is served from the target's rendered entry (after
   the target's context-window override and source request overrides), with `slug` and `id` set to the
   source and `display_name` set to the source's own display name when the registry has one, else the
   slug. The source keeps its own position in native-before-external ordering by the target's
   provider. Context-window overrides stored for the source do not apply while redirected; the
   catalogue UI shows them disabled. Rendering depends only on configuration and catalogue membership,
   never on account availability (same rule as the stable-catalog change).
6. **Visibility uses the hide switch.** Redirect sources are catalogue rows, so `hidden_models` applies
   to them. A redirect created for a slug outside the registry is hidden by default (the retired-model
   case); one created for a current catalogue model keeps that model's current visibility. Both are
   one click to change.
7. **Authorization on the requested model.** `allowed_models` is checked against `requested_model`
   (after key enforcement, before the redirect). Allowlists are written in the names clients send, and a
   key that allowed the retired model keeps working after the operator redirects it. A key that allows
   only the target does not gain the source. This differs from compaction routes, which skip when the key
   excludes the compaction model: a skipped compaction route still has a working coding model, while a
   skipped redirect would send a retired model upstream.
8. **Compaction routes see the served model.** A compaction route keyed on the target applies to
   redirected compaction requests. A compaction route keyed on a redirect source could never apply, and
   a compaction model that is a redirect source would bypass the redirect, so writes of either
   configuration are rejected with 400 `model_redirect_conflict` in both settings APIs.
9. **Response bodies keep the served model.** No CLIProxyAPI-style `force-mapping`. Codex ignores the
   body field, and the served model is the truthful answer for API clients and logs. The
   `OpenAI-Model` header is never forwarded on redirected requests (pinned by a test).
10. **Request logs.** `model` stays the served model, so pricing, reports and account attribution are
    unchanged. A nullable `requested_model` is written only when a redirect applied. The logs page shows
    `requested -> served`; the model filter matches either column.
11. **Continuity is a model switch.** Enabling, changing or removing a redirect is, for open
    conversations, the same as the client switching model: existing switch handling (cross-provider
    handoff, encrypted-reasoning portability, Claude thinking projection) applies unchanged, and the
    conversation loses its prompt cache once. Native-to-native continuation through
    `previous_response_id` follows the same upstream behaviour as a client model switch.
12. **Storage and cache.** `model_redirects(source_model PK, target_model, created_at, updated_at)`.
    A `DashboardRowsCache` snapshot invalidated through the cross-replica `settings` namespace, read
    once per request resolution and once per catalog build; past the TTL with the database unreachable,
    the last known rows keep applying.
13. **API.** `GET /api/settings/model-redirects` lists redirects with `status` (`active`/`inactive`)
    and `reason`, plus the eligible targets grouped by provider. `PUT /api/settings/model-redirects/{source}`
    (body `{"targetModel"}`) creates or replaces; `DELETE` removes (404 `model_redirect_not_found`).
    Writes validate the slug like context-window overrides, reject `source == target`, chains, unknown
    targets (400 `model_redirect_invalid` with a reason) and compaction-route conflicts, require
    dashboard write access and are audited as `settings_changed` naming `model_redirects`.
14. **Observability.** Each applied redirect logs `model_redirected request_id requested_model
    served_model surface` at info level.

## Surfaces

Covered: Codex Responses over HTTP and WebSocket (including owner-forwarded, non-streaming,
`/responses/compact`, `compaction_trigger` turns and client prewarm), `/v1/responses`,
`/v1/chat/completions`, Anthropic `/v1/messages` and `count_tokens`, and the three model lists.

Not covered: images (the image backend is fixed separately), transcriptions, embeddings, realtime,
and internal jobs (limit warmup, automations, cache probes), which name their models directly.

## Not covered

- Wildcard or pattern redirects (sub2api, OmniRoute).
- Per-account or per-API-key redirects (sub2api, CLIProxyAPI per credential).
- Fallback chains across models (OmniRoute and opencodex combos).
- Rewriting response bodies to the requested model (CLIProxyAPI `force-mapping`).
- A separate display name or description per redirect.
