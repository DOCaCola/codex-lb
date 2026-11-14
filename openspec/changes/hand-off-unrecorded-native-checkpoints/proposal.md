## Why

On 2026-11-14 at 19:09:53 UTC, switching chat `019f2859-8d1c-7891-8407-6052148b76d8` from GPT-6 Astra to Claude Opus 5.5 failed with `compaction_history_unavailable`. Claude received nothing. The chat was compacted natively on 2026-09-27, before handoff provenance existed (2026-10-01), and provenance is retained for 30 days anyway. Without provenance, the handoff refused to generate.

Since the 2026-10-16 portable-handoff change, provenance contributes only the model that summarizes the checkpoint: account selection is ordinary and checkpoints are readable by every OpenAI account. The conversation's own request log supplies that model just as well. Its newest successful native turn carried the conversation's checkpoints, so that model has read them; the Astra prewarm at 19:09:25 accepted this 48-day-old checkpoint.

The references recover no native checkpoint at all. opencodex replaces it with a fixed placeholder note, CLIProxyAPI and sub2api drop it, and OmniRoute rejects it.

## What Changes

- Without a valid provenance record, handoff uses the newest model that successfully served the same API key's conversation on an OpenAI account. Recorded provenance still takes precedence.
- The lookup is scoped by API key and by the conversation the destination turn identifies. Another key, another conversation or a client that names no conversation still fails with `compaction_history_unavailable`.
- Model access restrictions, claims, caching and retention are unchanged. The handoff start log names the model and which evidence chose it.
- Handoff summary records no longer carry the producing account, which nothing has read since the portable-handoff change.

## Impact

- Specs: `model-source-routing`.
- Code: `app/modules/proxy/checkpoint_handoff.py`, `app/modules/proxy/api.py`, `app/modules/request_logs/repository.py`.
- No settings, schema or client changes. Stored provenance and summaries keep their format.
