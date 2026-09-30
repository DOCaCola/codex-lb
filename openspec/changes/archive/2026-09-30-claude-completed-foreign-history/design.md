# Design

## Context

Production rejected a completed opaque-only foreign reasoning item at
2026-09-30T16:23:45Z. The inherited parent rollout has native OpenAI reasoning
with empty summaries and ciphertext, surrounded by visible messages and tool
pairs. The previous guard confused unavailable private reasoning with mandatory
conversation context.

## Goals / Non-Goals

Allow ordinary provider switches without losing retained history or weakening
active/signed continuation checks. No ciphertext decryption, invented summaries,
signatures, new upstream calls, live history changes or client fork.

## Decisions

1. Keep the existing completed-turn classifier and strict active/compaction
   refusals. Only completed foreign opaque-only items change behavior.
2. Replace such items in the temporary projection with empty plaintext reasoning.
   Claude's existing protocol renderer emits no block for that representation.
   This preserves input indices for subsequent authentication/tool diagnostics;
   no opaque value or lookup ID reaches Claude.
3. Preserve all readable summaries/content as assistant text, not signed thinking.
   Retained original input remains usable on its native provider path.
4. Log separate conversion/opaque-omission counts without content. Never swallow
   malformed summary/content or genuine Claude authentication failures.

## Reference evidence

CLIProxyAPI inspected 2026-09-30 at
`a270e7b9e57aaecd8f82555f44c2108518ad2330`: its Responses-to-Claude
convertResponsesReasoningToClaudeThinking omits foreign provider signatures from
the native request, explaining Anthropic rejects unsigned thinking. We apply
that lesson only to completed foreign state and additionally preserve readable
reasoning as text. This is source evidence, not independent OAuth qualification.

## Risks / Trade-offs

Claude cannot consume OpenAI's private encrypted reasoning. Continuing with
visible history is intentional, not lossless private-state transfer. Active
foreign continuation and full-state compaction still fail explicitly. Ordinary
native/OpenAI requests keep the retained ciphertext; no legacy rewrite is needed.

## Migration Plan

No migration or configuration change. Endpoint mocks must prove retained original
input, later replay, and strict refusal/authentication behavior before release.
