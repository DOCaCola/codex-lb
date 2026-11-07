# Classify Claude quota refusals by the binding hold

## Why

On November 7, a five-hour quota hold ending at 12:40 UTC overlapped a
model throttle ending at 12:22. Our routing selected the throttle's 503
classification but the quota's 18-minute retry delay. Codex kept the turn
active while sleeping instead of displaying exhausted quota.

OpenCodex PR #6995 (source inspected at d9ae8e595, routing unchanged at
36aa9e8f7) classifies the latest hold, with ties remaining transient.
Its reset time is separate from admission deadlines. We adapt that rule.

## What Changes

- Compare quota and transient cooldown horizons per account; shorter
  transient cooldowns no longer mask known later quota exhaustion.
- Keep authorization, credential and refresh exclusions authoritative.
- Retain conservative transient classification on ties or unknown quota
  horizons, and preserve mixed-pool classification and hard ownership.
- Report quota resets only from observed window reset times; cooldown
  deadlines still govern Retry-After and never fabricate resets.

## Verification

Regression tests cover real HTTP and WebSocket refusal envelopes, multiple
accounts, unknown reset times, deadline ties and preserved cooldown evidence.
No live upstream test requests are needed.
