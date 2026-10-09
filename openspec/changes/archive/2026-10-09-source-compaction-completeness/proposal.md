## Why
Source summarization reuses native OpenAI compact wire reduction, which trims
history to roughly 100k estimated tokens and removes images before the model
can summarize them. This can discard useful context even when Claude has
sufficient provider capacity. Completed output does not establish input coverage.

## What Changes
- Materialize source history before summarization without native wire trimming.
- Preserve text, tool results, images and readable checkpoint contents.
- Explicitly disable automatic upstream input truncation.
- Return provider capacity refusals and incomplete summaries without publishing
  a compaction checkpoint. Do not add approximate admission, staged generation,
  model-switch recovery or retry-on-capacity-error.
- Preserve native compact behavior and existing ownership/accounting contracts.

## Capabilities
### Modified Capabilities
- `model-source-routing`: complete source summarization history and atomic errors.

## Impact
Source compaction only, including Claude/OpenRouter/compatible providers and
dedicated endpoints/terminal triggers. No migration, client changes or deployment.
