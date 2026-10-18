# Compaction Routing

**Settings → Models → Model catalogue → Compaction routing** runs a coding model's native compaction on a different native model, for example compacting `gpt-6-astra` threads on `gpt-6-luna`. The client stays on its model. Only the compaction request moves, and the conversation continues on the coding model with the checkpoint the compaction model produced.

No route is configured by default, so every model compacts on itself.

## How it works

A request counts as a native compaction request in two cases:

- it is a `/responses/compact` request, on `/backend-api/codex/responses/compact` or `/v1/responses/compact`;
- its last top-level Responses input item is `{"type": "compaction_trigger"}`. This is how current Codex clients compact over WebSocket and over HTTP.

When a compatible route exists for the requested model, the proxy replaces `model` with the compaction model. If the route names an effort, it also replaces `reasoning.effort`; **Client's effort** keeps the client's effort. The rewrite happens during API key enforcement: after the key's model rules and before its effort policy. Account selection, request logs and costs therefore all see the compaction model. The Codex client ignores the server-reported model while compacting, so nothing changes on the client side.

Request logs show the routed model with operation `compaction`. Each applied route is logged as `compaction_model_routed` with the coding model, the compaction model and the effort.

## Compatibility rules

The rules are checked when a route is saved, which rejects it with HTTP 400 `compaction_route_incompatible`. They are checked again on every request, because the catalog can change after saving. A route that has become incompatible is skipped, logged as `compaction_model_route_skipped` with the reason, and shown as **Inactive** in the card.

| Reason | Meaning |
|---|---|
| `coding_model_unavailable`, `compaction_model_unavailable` | The model is not native, not offered to any account, or suppressed. |
| `nothing_changes` | Same model and no effort, so the route would do nothing. |
| `checkpoint_format_mismatch` | The models use different compaction checkpoint formats (`comp_hash`), so the coding model could not read the checkpoint. |
| `responses_lite_mismatch` | Only one of the two models uses Responses Lite. |
| `context_window_too_small` | The compaction model's context ceiling (`max_context_window`, else `context_window`) is below the window clients receive for the coding model, including overrides. |
| `input_modalities_missing` | The compaction model lacks an input type of the coding model, such as images. |
| `effort_unsupported` | The compaction model does not support the configured effort. |
| `compaction_model_routed` | The compaction model has a route of its own. Routes do not chain. |

Two API key rules also apply:

- If a key's allowed models exclude the compaction model, the route is skipped for that key (`reason=api_key_model_not_allowed`) and the request compacts on the coding model.
- If a key enforces a reasoning effort, the key's effort wins over the route's effort.

The routes live in `model_compaction_routes` and are managed through `GET`, `PUT` and `DELETE /api/settings/model-compaction-routes[/{slug}]`. Every change is audited as `settings_changed`. See the [model catalog contract](https://github.com/DOCaCola/codex-lb/blob/main/openspec/specs/model-catalog-compat/spec.md).

## Measured effect (October 2026)

We measured the effect on a Plus account's 5-hour usage, which the dashboard reports in whole percentage points. Each arm compacted three forks of the same 127k-token `gpt-6-astra` (medium) thread. Each fork then ran one follow-up Astra turn. Usage was read only after the upstream counters had settled.

| Compaction ran on | Compactions (3×) | First Astra turn after (3×) | Total points | Checkpoint size (encrypted chars) |
|---|---|---|---|---|
| Astra itself (baseline) | 5–6 | 2 | 7–8 | 26.7k–35.9k |
| Luna, client-side `/model` switch | 0 | 5 | 5 | 6.3k–10.8k |
| Route → `gpt-6-luna`, client's effort | 0 | 5 | 5 | 9.1k–14.5k |
| Route → `gpt-6-luna`, max effort | 0 | 5 | 5 | 12.0k–16.3k |
| Route → `gpt-6.1-sol`, client's effort | 2 | 5 | 7 | 36.0k–41.8k |

Each compaction read about 123.6k input tokens with no cache hits.

| Compaction model | Duration | Output tokens | API-equivalent cost |
|---|---|---|---|
| Luna | ~7 s | 0.6k–1k | ~$0.013 |
| Luna max | ~9 s | 0.8k–1.2k | ~$0.013 |
| Sol 6.1 | ~45 s | 2.9k–3.3k | ~$0.27 |

Summary quality was equivalent in every arm. Each thread answered a request for a 10-point summary of the work so far with 1.04k–1.29k characters. The Luna max and Sol 6.1 checkpoints kept slightly more specifics.

### Why the first turn after a foreign checkpoint costs more

After compacting on itself, the first Astra turn cost 2 points. After a checkpoint from another model, it cost 5 points in every arm. The cause is not the client's model-switch message, because routed threads contain none and cost the same. Two effects add up:

- **Lost warm-up cache.** Codex sends an 11.8k-token warm-up request (`generate: false`) before the turn. After its own checkpoint, Astra reused that cache in 3 of 3 turns. After a foreign checkpoint, it reused the cache in only 2 of 9 turns. This happens upstream, and codex-lb cannot influence it.
- **Larger context.** The continuation input was about 19.4k–22.8k tokens against about 17.0k after Astra's own checkpoint.

The penalty applies once, on the first turn. Later turns cache normally.

### Recommendation

Route `gpt-6-astra` to `gpt-6-luna`, preferably at **max** effort. It saved 2–3 of 7–8 points per three compactions, about a third, and compacts in seconds rather than minutes. Max effort costs the same and produces a slightly richer checkpoint. Routing to `gpt-6.1-sol` saves almost nothing, because its compaction usage cancels out its advantage over Astra.

These are small samples measured in whole points, so treat the numbers as directional. Savings grow with how often a thread compacts, and shrink if the account's plan prices the compaction model differently.

## Operational notes

- A route only takes effect when an account offering the compaction model is routable. A newly unpaused account becomes routable at the next model-catalog refresh, up to 5 minutes later. Until then, requests that need its models fail with `No accounts with a plan supporting model …`.
- Clients without remote compaction (provider name other than exactly `OpenAI` in `config.toml`) compact locally with ordinary Responses requests. Those are not native compaction requests, so routes do not apply to them.
- Codex's `/model` switch before compacting gives the same savings without a route, but leaves the switch message in the thread. Related upstream Codex issues: [openai/codex#54255](https://github.com/openai/codex/issues/54255) on switch messages across compaction, and [#22486](https://github.com/openai/codex/issues/22486) and [#25778](https://github.com/openai/codex/issues/25778) requesting a dedicated compaction model. [codex-compact-model](https://github.com/KristijanPruzinac/codex-compact-model) solves the same problem as a local router but compares `context_window` only; codex-lb compares against the context ceiling.
