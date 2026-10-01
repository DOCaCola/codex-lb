# Design

## Context

`build_source_compaction_request` appends a user message containing
`COMPACTION_PROMPT` to the complete client history. The Claude preparer then
runs `project_foreign_replay` with `require_complete_history=True`, which
rejected every non-Claude `encrypted_content`, historical or active. Without that
flag, only foreign ciphertext at or after the last user/task input is rejected.
Because the summarizer instruction is itself a user message, compaction could
not reuse that rule unchanged; the blanket rejection was chosen instead
(`2026-09-30-claude-provider-history` decision 4, "a display summary cannot prove
the full encrypted state survived").

## Goals / Non-Goals

**Goals:** compaction after a provider switch behaves like a normal turn on the
same history, including immediate `/compact` after switching; open foreign tool
loops still fail explicitly.

**Non-Goals:** decoding or summarizing foreign ciphertext, changing signed Claude
history rules (cross-Claude-model compaction stays strict), handing compaction
back to the original provider, the plaintext-only open-tool-loop gap.

## Decisions

1. **Boundary on client history.** In compaction mode the final input item is the
   builder-owned instruction. It is split off by a shared helper that asserts the
   invariant, not by matching prompt text. The active turn start is then
   `len(history)` if the history ends with an assistant `message` (closed turn),
   else the last user/external-task index, exactly as for normal turns. Paired
   tool outputs still do not close a turn.
2. **Closed means a final assistant message.** Codex records interrupts as a
   `<turn_aborted>` user message (openai/codex `d6c3b44`,
   `core/src/context/turn_aborted.rs`), so interrupted turns are already closed
   by the user rule. A completed turn ends with its assistant answer; compacting
   it is equivalent to a new user turn. Commentary messages inside a tool loop
   are not final items, so an open loop ending in tool output stays active.
3. **Superseding the complete-history rejection.** Compaction replaces history
   with a Claude-generated summary; Claude can only summarize what it can read,
   and every normal Opus turn already proceeds without foreign private state.
   Refusing gives the user no better outcome than switching providers manually.
   The original ciphertext remains in the client/retained history until the
   compaction succeeds, and a failed compaction changes nothing.
4. **Error wording.** The open-loop refusal uses the active-continuation message
   for both modes; "Complete compaction contains…" no longer exists.

## Reference evidence (inspected 2026-10-01)

- OpenCodex `ef0297f`: strips reasoning `encrypted_content` on serving identity or
  account change, including routed compaction; Anthropic adapter skips thinking
  without a real signature.
- Sub2API `d6adebd`: decodes only its own envelope; other reasoning is skipped.
- CLIProxyAPI `fd48ea6`: drops unsigned reasoning; returns 501 for Claude
  `/responses/compact`.
- OmniRoute `dbe703a0`: drops incompatible opaque reasoning by default.

None refuses compaction for completed foreign reasoning. Our rule keeps the
stricter open-loop refusal, because Anthropic requires signed thinking before a
continued `tool_use` when thinking is enabled.

## Risks / Trade-offs

- Opaque-only foreign reasoning is not represented in the summary. This matches
  normal turns and all inspected references.
- A client that ends a closed turn without an assistant message (and without a
  turn-aborted marker) is treated as open and refused explicitly, not silently.
