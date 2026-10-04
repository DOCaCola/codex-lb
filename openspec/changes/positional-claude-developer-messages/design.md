# Design

## Context

Anthropic's mid-conversation system messages must immediately follow a user turn (one carrying tool results counts), must precede an assistant turn or end the messages array, and cannot be the first message. Consecutive system messages are one section. Codex records developer updates before the user message of the turn they apply to, and occasionally between assistant items of a tool loop.

## Decisions

1. **Only leading messages are prompt-level.** A developer/system item seen before any message has been projected joins the system prompt with `instructions`, as before. That prefix is fixed for the conversation.
2. **Later messages wait for the next legal boundary.** They accumulate and are emitted when the projection is about to append an assistant turn and the last message is a user turn, or at the end of the request after any `(continue)` turn. The placement depends only on preceding items, so a later request reproduces it byte for byte and the cached prefix only grows.
3. **Capability decides the form.** Models whose policy declares mid-conversation system support receive a `system` turn. Others, including models without a qualified policy, receive the blocks between `<system-reminder>` delimiters at the end of the preceding user turn, the form OAuth relocation already uses for such models. Both keep block contents unchanged.
   The policy matches observed native traffic: CLIProxyAPI's captures of Claude Code show system turns, with the mid-conversation beta, only on Opus 5 and Sonnet 5, and a measured rejection only on older models. Anthropic's documentation lists Sonnet 5 as unsupported without the beta; the beta is always sent with system turns.
4. **Relocation stays separate.** Relocated prompt-level instructions are still inserted after the first ordinary user turn; a positional system turn may follow them directly, which Anthropic treats as one section. The mid-conversation beta is sent whenever any system turn is present.
5. **Recovery ignores system turns.** The open tool turn walk skips them, so a system turn after the last tool result does not expose the open turn's signed thinking to stripping.

## Risks

- One cache rewrite per active conversation after deployment when its history holds later developer messages.
