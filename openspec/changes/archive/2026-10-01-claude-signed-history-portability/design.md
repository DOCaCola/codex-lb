# Design

## Context

`authenticate_replay` marked every signed block strict when
`require_complete_history` was set, so compaction required the original
account/model for all signed history and `open_responses` skipped signature
recovery for compaction. The rule came from the intent that the summarizer sees
all context; refusal was chosen because the only available degradation (omission)
loses content. Normal turns omit mismatched completed blocks and recover signature
rejections by stripping historical thinking.

`project_responses` enables `{"type":"enabled","budget_tokens":N}` for
budget-thinking models whenever reasoning is requested, independent of history.

## Goals / Non-Goals

**Goals:** compaction keeps every readable part of completed signed history on
any eligible route; translated budget-thinking requests never violate the
manual-mode turn structure.

**Non-Goals:** replaying a signature on an account or model other than the one
that produced it; making active-turn or search state portable; changing native
Messages; the `thinking-binding-controls` beta; disabling thinking for adaptive
models (Opus 5.5 and Fable reject every off switch).

## Decisions

1. **Compaction reads; continuation follows Anthropic filtering.** Anthropic
   allows omitting prior-turn thinking outside the active tool turn, and filters
   prior-turn blocks per model anyway (Haiku keeps only the last turn). Normal
   turns therefore keep omission. A compaction request exists to summarize the
   context, so completed thinking that cannot keep its signature is converted to
   readable assistant text. Redacted thinking has no readable content and is
   omitted. This is Sub2API's retry strategy ("preserve content as text",
   `FilterThinkingBlocksForRetry`, `d6adebd`), applied deterministically.
2. **One boundary.** `authenticate_replay` uses the same `_active_turn_start` as
   foreign projection, so the summarization instruction never makes a completed
   turn active. Strictness is then: hosted search, or index at/after the active
   start. Compaction-specific owner/model errors disappear; active conflicts keep
   the active-turn errors. Completed blocks only express a preferred account,
   so the original account still serves the summary when eligible and its
   signatures are replayed verbatim.
3. **Owner conflicts.** OmniRoute (`dbe703a0`) observed signatures surviving an
   OAuth account switch on the same model, but Sonnet 5.5 blocks are documented
   as account-bound. Converting mismatched completed blocks to text avoids
   depending on either claim.
4. **Compaction recovery.** On the existing one-shot signature 400, compaction
   converts unprotected historical thinking to text and drops redacted thinking,
   instead of refusing. The trailing tool chain stays protected; server-tool
   requests remain excluded. Normal and native recovery are unchanged.
5. **Unsigned open tool turn.** Anthropic: "the entire turn runs in a single
   thinking mode"; manual mode additionally requires the final assistant turn to
   begin with a thinking block; adaptive mode relaxes this, and mid-turn
   toggles silently disable thinking for that request. Claude Code issue #14264
   shows the manual-mode 400 in practice. After projection, the open turn is the
   messages after the last user message without a `tool_result`. If its first
   assistant message does not start with `thinking`/`redacted_thinking`, a
   budget-mode request sends `{"type":"disabled"}`, the value Claude Code itself
   sends and the documented thinking-off setting for Haiku 4.5 and Sonnet 4.5
   (OpenCodex `ef0297f` live table: Haiku 4.5 accepts it). Effort validation is
   unchanged; the next user turn re-enables thinking. Sub2API reaches the same
   end state reactively, by deleting top-level thinking after "Expected
   `thinking`" 400s; the structure is known before dispatch, so no rejected
   request is spent. CLIProxyAPI `fd48ea6` disables thinking only for forced tool
   choice; OpenCodex replays only genuine signatures and does not cover this case.

## Risks / Trade-offs

- Thinking-as-text adds tokens to compaction on a changed route; it is bounded by
  content the original route would also have read on keep-all models.
- Fable 5.1+ prefix binding: projection is a pure function of route and history,
  so later blocks on one route see a stable prefix. Not live-qualified.
- The disabled turn produces no thinking for that response. Quality impact is
  limited to one request inside an already thinking-less turn.
