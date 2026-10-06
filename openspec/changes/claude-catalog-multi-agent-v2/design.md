## Context
Codex 0.160.1 persists `multi_agent_version` per thread when the root starts, taken from the root model's catalog entry. A v1 tree stays v1 and a v2 tree stays v2 for its lifetime, whatever the catalog later says. The native OpenAI `gpt-6.1-sol` entry already advertises v2.

## Decisions
- **Projection point.** Set the field in the Claude block of `_to_upstream_model`, next to `apply_patch_tool_type`. It runs on every catalog projection, so it survives source refresh and model re-sync. It is unconditional because the served catalog does not vary by client version.
- **Scope.** Claude only. OpenRouter and OpenAI-compatible sources already receive portable `agent_message` user turns and could advertise v2 later, but no client tree has been validated against them.
- **Header.** Codex's `InterAgentCommunication` input item already contains its header in the plaintext content. codex-lb lowers that content unchanged; it adds no header of its own.
- **Cross-route history projection.** v2 defaults `fork_turns` to `"all"`, so children replay the parent's history on their own provider. Unrepresentable provider state is translated, not rejected:
  - *Redacted thinking* has no readable content and no representation outside its Claude model, so it is omitted toward OpenAI. This matches completed redacted thinking on another Claude model, which is already omitted.
  - *Hosted search toward another provider* becomes one assistant `output_text` message at the call's position: `Web search: <query>` (or `Opened page: <url>`, `Found in page <url>: <pattern>`), then `Sources:` with one `<title> — <url>` line per result. Claude results supply title and URL from `web_search_result`. OpenAI results supply them from `action.sources` when the client included it, otherwise the query alone. This applies to completed and active turns, as foreign reasoning already does.
  - *Completed Claude search toward another Claude model or account* uses the same text projection. Active-turn search between Claude routes keeps its owner and model, as active signed thinking does.
  - The rendering is deterministic, so a child or switched conversation keeps a stable cacheable prefix across turns. Retained logical history keeps the original items, and returning to the original route replays them natively.
  - Projection logs gain `redacted_omitted` and `search_projected` counts, never content.
- **Why text, not a structured `web_search_call`.** CLIProxyAPI keeps a structured `web_search_call` toward OpenAI by minting `ws_<srvtoolu id>` identities. codex-lb's native boundary removes foreign identities and never fabricates them, and a Claude call has no `ws_` ID. Whether OpenAI accepts an ID-less or foreign-ID `web_search_call` input item can't be established without live probes, which this work doesn't use. Assistant text is accepted on both providers, and it carries the same readable content the references keep. opencodex reduces Claude search results to sources and text, and Sub2API carries only the answer text.
- **Not fabricated.** Encrypted Claude search results are never rebuilt from citations or text, and no signatures, search calls or server-resource ownership are created. Native Claude Code resource provenance is unaffected.

## Reference survey (inspected 2026-10-06)
- CLIProxyAPI `a2976eb`: redacted thinking travels as `claude-redacted-thinking:<data>`, which no foreign upstream accepts as a signature, so it is dropped there. A server_tool_use + web_search_tool_result pair folds into `web_search_call` (`ws_` ID, query, readable results) and is rebuilt on return to Claude.
- opencodex `beba8b7`: `opaque-state.ts` drops `redacted_thinking` whole and strips signatures for non-Anthropic destinations. Its search sidecar keeps text and URL/title sources. An opt-in `enforce` compatibility mode can refuse lossy translation, but it is off by default.
- Sub2API: in Chat bridging, redacted thinking "contribute[s] nothing". Claude search results aren't converted; the answer text carries them.

## Lab validation (synthetic, closed network)
Stock 0.160.1 and fork 0.160.1-doca, roots and children on Claude and GPT (claude→gpt, gpt→claude, claude→claude):
- Roots and children persist v2 with canonical paths `/root` and `/root/worker`. Children get native `send_message`.
- OpenAI receives the `collaboration-optimize` namespace without `encrypted` markers. Claude receives the messages as user text.
- A waiting parent receives the progress note and the final answer. A `followup_task` turn reports once.
- Existing v1 trees resumed under the new catalog stay v1, with the same tools.

### Lab case: full-history forks and route switches
Same closed lab, mocks only, stock 0.160.1 and fork 0.160.1-doca. The mocks return Claude thinking, redacted thinking and a hosted search, and OpenAI encrypted reasoning with a `web_search_call` carrying `action.sources`. All twelve runs completed without errors:
- **Full-history forks** (Opus→GPT, GPT→Opus, Opus→Sonnet) never carry foreign state. Codex's `keep_forked_rollout_item` keeps only system/developer/user messages and assistant messages with `phase: final_answer`; reasoning, `web_search_call` and tool items are dropped. The child's task arrives last, as an `agent_message` (a user turn on Claude).
- **Compacted parent → GPT child**: the child receives the Claude compaction summary and no Claude envelope. Replacement history is the one place forked history keeps non-message items, so it is where the projection applies to children.
- **Same-thread model switches** (Opus→GPT→Opus, GPT→Opus→GPT, Opus→Sonnet→Opus) exercise the projection directly. The foreign route receives `Web search: lab weather` text with Claude's sources and no Claude envelopes, signatures, redacted data or `srvtoolu` IDs; Claude never receives OpenAI ciphertext or `ws_` IDs. Codex drops `action.sources` and the call `id` from OpenAI `web_search_call` history, so Claude sees the query alone. Returning to the original route replays the native blocks with their original signatures; consecutive requests on the original route extend one another apart from the moving `cache_control` marker.

Two pre-existing issues surfaced, outside this change:
- The Claude adapter emits assistant messages without `phase`, so Codex drops a Claude parent's answers from every forked child.
- On WebSocket `previous_response_id` turns, developer messages that request normalization lifted into `instructions` on the first turn are not part of the retained input, so Claude loses them from the second turn on (26,688 → 21,778 characters in the lab; HTTP full resends keep them).

## Client limitations (not codex-lb)
- Direct user input to a v2 subagent is rejected (`can_accept_direct_input`). Users reach the child through the parent's `followup_task`.
- An idle parent is not woken by child mail (`trigger_turn: false`). The mail is drained into the parent's next user turn but sampled only after that turn's answer, so the model sees it one user turn later (`run_turn` defers pending input at turn start, `MailboxDeliveryPhase::NextTurn`).
- v2 ignores `agents.max_depth` and limits concurrency instead.

## Rollout
Clients refresh the catalog within the 300 s cache TTL or on restart. Only new trees adopt v2. Removing the field rolls back new trees; v2 trees already created stay v2, and their messages remain portable because they are plaintext.
