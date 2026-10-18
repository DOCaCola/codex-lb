# Route Native Compaction to a Configured Model

## Why

Codex compacts a conversation with the model that is coding in it. Compaction only summarizes, so it can run on a
cheaper model of the same generation. Codex has no setting for this (openai/codex#22486, #25778, open). Switching the
thread to the cheaper model around `/compact` costs more than it saves: Codex rebuilds the post-compaction context for
the model active at compaction time, so the compactor's `<model_switch>` instructions survive compaction and the switch
back adds a second set. On DOCa Plus (2026-10-18, 127k-token fork) three Luna compactions saved about 2-3 five-hour
points net, most of the Luna saving lost to the first Astra turn afterwards (5 points versus 2).

A gateway rewrite avoids that cost: the client keeps its coding model, so Codex builds the replacement history for it,
and only the upstream compaction request runs on the cheaper model. KristijanPruzinac/codex-compact-model (inspected
at 26e3bc5, 2026-09-25) does this in a local router that changes only `model` and `reasoning.effort` on native
compaction requests and requires an identical checkpoint format (`comp_hash`), a large enough context window, the same
input types and a supported effort.

Probed on the ChatGPT backend (2026-10-18, DOCa Plus): on one WebSocket, `gpt-6-luna` continued a `gpt-6-astra`
response through `previous_response_id`, compacted it through `compaction_trigger`, and `gpt-6-astra` resumed from
Luna's `compaction` item on a new connection. Codex ignores the server-reported model during compaction
(`compact.rs` `drain_to_completed`, `compact_remote_v2.rs`), so a different model there raises no reroute warning.

## What Changes

- A dashboard-managed route per native coding model names a native compaction model and optionally a reasoning
  effort (`model_compaction_routes`, Settings -> Model catalogue).
- A route is compatible while both models are native catalog models with the same non-empty `comp_hash` and Responses
  Lite capability, the compaction model's context ceiling covers the window clients receive for the coding model, it
  accepts every input type of the coding model, supports the configured effort and has no route of its own. Writes
  reject incompatible routes; requests re-check them against the live catalog and skip a route that became
  incompatible, logging why.
- Native compaction requests (a terminal `compaction_trigger` or `/responses/compact`) on a routed coding model are
  rewritten once, after API-key model enforcement and before effort policy, on every Responses surface. Routing,
  continuity, account allow-lists, request logs and costs then see the compaction model. An API key that cannot use the
  compaction model keeps the coding model; an API key that enforces an effort keeps it.

## Capabilities

### Modified Capabilities

- `model-catalog-compat`: native compaction model routes.
