# Convert Checkpoints on the Economy Model

## Why

A switch from a native model to a source model converts the conversation's encrypted compaction checkpoint into a
readable summary through a native request. That request ran on the model that produced the checkpoint, usually
gpt-6.1-sol or gpt-6-astra. A controlled measurement on a Plus account (127k-token conversation, three forks per arm)
found Luna compaction took about 5 s instead of 45-57 s on Astra and used about one 5-hour quota point less per
compaction, with summaries that let every follow-up turn describe task, decisions and next step correctly. Luna's
summaries were about 6k tokens larger, which made the next Astra turn cost more; a handoff's next turn goes to the
source model instead, so that penalty does not apply to the native quota.

No reference converts native checkpoints (opencodex replaces them with an opaque note, CLIProxyAPI drops them,
OmniRoute rejects them), so there is no prior art for the model choice.

## What Changes

- Handoff generation runs on the economy model of the checkpoint's generation (gpt-6-luna for GPT-6, gpt-5.6-luna
  for gpt-5.6) when the catalog offers it and the API key may use it, otherwise on the original model.
- The handoff log line records the original and the conversion model. Cached summaries stay attributed to the
  original model, whose access later reuse checks.

## Risk

Whether gpt-6-luna reads a gpt-6.1-sol or gpt-6-astra checkpoint is unverified (the measurement had Astra read a Luna
checkpoint); experiments against the real upstream are out of scope. A rejection surfaces as the existing explicit
handoff failure.

## Capabilities

### Modified Capabilities

- `model-source-routing`: On-demand native checkpoint handoff.
