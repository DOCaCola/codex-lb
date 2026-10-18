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

Primed forks first ran one real Astra turn, as a live thread does just before auto-compaction. Only the baseline and the last two arms were primed; the other arms were not, and that skews their first turn (see below). The baseline and the first primed Luna max arm were primed with "reply with exactly the word OK and nothing else"; the last arm with a realistic question about the thread's content.

| Compaction ran on | Primed | Compactions (3×) | First Astra turn after (3×) | Total points | Checkpoint size (encrypted chars) | First turn cached |
|---|---|---|---|---|---|---|
| Astra itself (baseline) | yes | 5–6 | 2 | 7–8 | 26.7k–35.9k | 11,648 on all 3 |
| Luna, client-side `/model` switch | no | 0 | 5 | 5 | 6.3k–10.8k | 0, 6,400, 6,400 |
| Route → `gpt-6-luna`, client's effort | no | 0 | 5 | 5 | 9.1k–14.5k | 0 on all 3 |
| Route → `gpt-6-luna`, max effort | no | 0 | 5 | 5 | 12.0k–16.3k | 0, 6,400, 0 |
| Route → `gpt-6.1-sol`, client's effort | no | 2 | 5 | 7 | 36.0k–41.8k | 0, 0, 11,648 |
| Route → `gpt-6-luna`, max effort | yes ("OK") | 0–1 | 1 | 2 | 2.1k–2.9k | 11,648 on all 3 |
| Route → `gpt-6-luna`, max effort | yes (question) | 0–1 | 0–1 | 1 | 4.1k–8.8k | 11,648 on all 3 |

Each routed compaction read about 123.6k input tokens (129.2k when primed) with no cache hits.

| Compaction model | Duration | Output tokens | API-equivalent cost |
|---|---|---|---|
| Luna | ~7 s | 0.6k–1k | ~$0.013 |
| Luna max | ~9 s | 0.8k–1.2k | ~$0.013 |
| Sol 6.1 | ~45 s | 2.9k–3.3k | ~$0.27 |

Each thread then answered a request for a 10-point summary of the work so far. In the unprimed arms and the question-primed Luna max arm, the answers were equivalent (1.04k–1.29k characters); the Luna max and Sol 6.1 checkpoints kept slightly more specifics. The "OK"-primed Luna max arm is the exception, described under [Checkpoint quality](#checkpoint-quality).

### Why the unprimed first turns cost more

In the unprimed arms, the first Astra turn after compaction cost 5 points, against 2 in the baseline. The cause is the test setup, not the foreign checkpoint.

Upstream prompt caching is keyed by the thread, which Codex sends as the prompt cache key. A turn after compaction can reuse only the system prompt and tools, about 11.6k tokens; the checkpoint itself is new input either way. That prefix is cached only if Astra recently ran a real request under the same key:

- **Baseline:** the forks had a real Astra turn and then an Astra compaction under their own keys. Every follow-up reused 11,648 tokens.
- **Unprimed routed arms:** the forks were fresh, and their compaction ran on Luna or Sol, so Astra had served nothing real under their keys. Follow-ups mostly paid the full ~19.5k input uncached.
- **Primed Luna max arm:** one real Astra turn before the routed compaction was enough. All three follow-ups reused 11,648 tokens and cost 1 point together.

Codex's warm-up request (`generate: false`, about 11.8k tokens before each turn) does not fill that cache. The priming turns, sent four seconds after a warm-up with the same prefix, got 0 of 129k tokens cached. The warm-ups also did not show up in 5-hour usage. codex-lb still prices them at the uncached rate, so its API-equivalent cost overstates warm-up traffic.

In a live thread, the turn that triggers auto-compaction runs seconds before the compaction under the same key, so the primed result is the realistic one. The model-switch message is not a factor either: routed threads contain none.

### Checkpoint quality

In the "OK"-primed arm, Luna max wrote checkpoints of only 57–117 output tokens (2.1k–2.9k encrypted characters), a fifth of the unprimed Luna max checkpoints. The follow-up answers lost most specifics and stated that the earlier explanations were unavailable. Astra compacting history that ended in the same instruction produced 2.2k–2.9k output tokens and kept full detail.

Rerun with a realistic question as the priming turn, Luna max wrote 204–581 output tokens (4.1k–8.8k encrypted characters), and every follow-up summarized the whole conversation, including the latest exchange. The "OK" instruction caused the loss: Luna applies a strict output constraint in the latest user turn to its own summary as well, while Astra does not.

Normal auto-compaction, mid-turn after tool output, is not affected. The risk is a manual `/compact` right after a user message that restricts the answer's length or format, such as "answer only yes or no".

### Reading 5-hour usage

5-hour usage does not follow API-equivalent cost linearly. The three primes, 387k uncached Astra input tokens priced at $3.88, cost 8 points, while three unprimed follow-ups of about 58k uncached tokens cost 5. Whole-point readings also round. Compare arms only roughly; the cached-token counts are the reliable signal.

### Recommendation

Routing `gpt-6-astra` compaction to `gpt-6-luna` max cuts the cost of compaction plus the next turn from 7–8 points to about 2 in a live thread, and compacts in seconds rather than a minute. Max effort costs the same as the client's effort and produced richer checkpoints in the unprimed arms. Watch checkpoint quality, given the result above.

`gpt-6.1-sol` writes Astra-sized checkpoints and costs about 2 points per three compactions. Its unprimed first-turn penalty is the same test artifact, so in a live thread it would likely cost about 3–4 points in total. That figure is inferred, not measured primed. It is the safer choice when checkpoint detail matters more than speed.

These are small samples measured in whole points, so treat the numbers as directional. Savings grow with how often a thread compacts, and shrink if the account's plan prices the compaction model differently.

## Operational notes

- A route only takes effect when an account offering the compaction model is routable. A newly unpaused account becomes routable at the next model-catalog refresh, up to 5 minutes later. Until then, requests that need its models fail with `No accounts with a plan supporting model …`.
- Clients without remote compaction (provider name other than exactly `OpenAI` in `config.toml`) compact locally with ordinary Responses requests. Those are not native compaction requests, so routes do not apply to them.
- Codex's `/model` switch before compacting gives the same savings without a route, but leaves the switch message in the thread. Related upstream Codex issues: [openai/codex#54255](https://github.com/openai/codex/issues/54255) on switch messages across compaction, and [#22486](https://github.com/openai/codex/issues/22486) and [#25778](https://github.com/openai/codex/issues/25778) requesting a dedicated compaction model. [codex-compact-model](https://github.com/KristijanPruzinac/codex-compact-model) solves the same problem as a local router but compares `context_window` only; codex-lb compares against the context ceiling.
