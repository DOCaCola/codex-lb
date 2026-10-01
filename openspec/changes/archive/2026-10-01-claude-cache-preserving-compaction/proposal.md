## Why
Codex compaction on a Claude OAuth account reads nothing from the prompt cache.
Production conversation 01a0e444 compacted 161,933 input tokens with 0 cache
reads and 161,929 cache writes ($0.94), between turns that read 98% and 74% from
cache. Source summarization drops the conversation's tool declarations, and
Claude caches tools before system and messages, so the whole prefix misses.

## What Changes
- Claude summarization keeps the client's tools, tool_choice and
  parallel_tool_calls on the compact endpoint and on terminal compaction triggers.
- The summarization instruction ends with a short no-tools, plain-text reminder.
- Tool, custom-tool or hosted-search output fails compaction with
  model_source_compaction_invalid; no checkpoint, history unchanged.
- OpenRouter and other sources stay tool-free; native compact is unchanged.

## Capabilities
### Modified Capabilities
- `model-source-routing`: source compaction history safety.

## Impact
Claude compaction cost and latency. No schema, migration, configuration,
client or native OpenAI compact change.
