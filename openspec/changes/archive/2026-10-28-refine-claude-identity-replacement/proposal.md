# Refine Claude identity replacement

## Why
The 2026-10-28 audit of `3e0afe59f` found a short post-replacement window without
routable models, generic non-retryable errors for replacement races, and mismatch
messages that did not mention the new replacement option.

## What Changes
- Keep the discovered catalog and selected models while marking discovery due.
- Return thread_not_found/resource errors for resource-bound races and retryable
  claude_identity_changed otherwise.
- Name the replacement option in reconnect mismatch messages.
