# Design — Restrict Public Text Backfill to Messages

## Context

`_synthetic_text_delta_for_output_item()` exists for providers that finish a
response with message text in `response.output_item.done` or terminal
`response.output`, but omit the incremental `response.output_text.delta`.
Before extracting text, the helper normalizes provider-specific textual items
into public assistant messages. Reasoning is already a public output-item type,
so normalization intentionally preserves its `type: "reasoning"` discriminator.

The bug is that text extraction runs after normalization without checking that
discriminator. Its generic content scan accepts any content part carrying a
`text` field, including LiteLLM reasoning content.

## Decision

Use the normalized output-item type as the semantic gate for visible-text
backfill. Only `type: "message"` is eligible. This retains compatibility for
provider-specific final-answer items because the existing public normalizer
converts those textual items into assistant messages, while public reasoning,
tool, compaction, and other output-item types remain ineligible.

Do not special-case provider names, reasoning event names, or the
`enable_thinking` request option. The output-item discriminator is the public
Responses contract boundary and applies consistently to direct item-done and
terminal-output fallback paths.

## Validation

- Existing message-only item and terminal backfill tests continue to pass.
- A focused unit regression verifies that a reasoning item containing text does
  not produce an output-text delta.
- A model-source route regression mirrors LiteLLM's interleaved
  `response.reasoning_text.*` and `response.output_text.*` stream and verifies
  reasoning remains reasoning while visible text is emitted exactly once.
