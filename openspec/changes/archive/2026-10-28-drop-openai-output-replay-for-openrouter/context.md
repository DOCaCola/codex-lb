# Context

Found in the 2026-10-28 audit of `27d6f12f0`. Codex source `970111f`
(`codex-rs/core/src/client.rs`) appends the include only for OpenAI providers; its
`output_token_replay.rs` states that stored ciphertext survives provider changes.
Production clients name codex-lb `OpenAI`, so OpenRouter models receive the same
include. Production OpenRouter Responses projection added
`provider.require_parameters: true`. No OpenRouter request exercised the path after the
include was accepted, so an upstream rejection is unproven; no live experiment was run.

Claude translation already ignores non-reasoning `encrypted_content`. Reasoning items
keep the existing OpenRouter behavior; this change is limited to output replay.
For example, `include: ["reasoning.encrypted_content", "output.encrypted_content"]`
becomes `["reasoning.encrypted_content"]`, and an assistant message keeps its text but
loses its OpenAI `encrypted_content`.
