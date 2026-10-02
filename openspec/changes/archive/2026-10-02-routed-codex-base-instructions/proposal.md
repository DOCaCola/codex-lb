## Why
Codex renders a catalog row's instruction template literally. Native rows receive the live Codex agent prompt from the ChatGPT catalog, but Claude, OpenRouter and OpenAI-compatible rows go out with an empty `base_instructions`, so Codex sessions on routed models run without any Codex agent prompt. This was an omission: upstream codex-lb #331 left the field empty because native rows are filled by the live refresh, and routed rows have no live source.

All three references give routed models the real prompt: Sub2API since its routed catalog (`e471be73`), with the GPT identity removed in PR #7308 after the identity line caused repeated 429s through a non-OpenAI gateway; opencodex with a neutralised identity named per request (issue #5217: Codex replays a parent's stored instructions into subagents on other models); CLIProxyAPI until its catalog crossed Codex's 1 MiB limit (`673131f5`).

## What Changes
- Routed Codex catalog rows carry the live prompt of the default listed native model (lowest priority, slug tie-break), with the GPT identity sentence neutralised. The prompt is model-neutral and identical for every API key.
- When no native prompt exists (bootstrap catalog before the first live refresh), routed rows keep an empty prompt and the catalog build logs a warning.
- Routed Responses requests name the destination model's display name in the Codex identity sentence at dispatch time, covering both the neutral catalog prompt and a native prompt replayed into a routed subagent. Instructions without a Codex identity sentence are unchanged.
- The catalog build logs an error when the Codex catalog body exceeds Codex's 1 MiB `model_catalog_url` limit.

Unchanged by decision: deferred tool search, code mode, multi-agent version, web search content types and the Claude context cap.

## Capabilities
### Modified Capabilities
- `model-catalog-compat`: routed catalog entries carry the neutral Codex prompt; catalog size is checked against the client limit.
- `model-source-routing`: routed Responses requests name the destination model in the Codex identity.

## Impact
Codex catalog build and routed Responses payload shaping. Native rows, native Claude Messages passthrough, Chat Completions and storage are unchanged. Routed first-turn input grows by the prompt (about 5k tokens), which prompt caching absorbs on later turns.
