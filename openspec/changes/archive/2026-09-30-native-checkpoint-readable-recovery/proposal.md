# Proposal

## Why

Switching from native OpenAI to Claude after remote compaction fails because the
checkpoint is encrypted. Dropping it would hide lost conversation context; we
need verified readable recovery without retaining protocol debris.

## What Changes

- Bind successful native checkpoints to their complete readable compact input,
  scoped by authenticated API key and conversation.
- Retain semantic messages, readable reasoning, direct tool pairs and attachments;
  exclude telemetry, advertisements, local markers and provider ciphertext.
- Resolve known checkpoints before source inference or compaction, including
  chained checkpoints and retained continuations. Reject unavailable state.
- Reuse bounded private replay storage and its one-hour expiry. Keep native
  upstream requests and checkpoints unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-source-routing`: verified readable checkpoint recovery and retention.

## Impact

Native compact completion, source request materialization and focused regression
coverage. No client fork, new settings, database migration or deployment.
