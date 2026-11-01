## Why

The translated Claude path advertised the daily-followed CLI version (2.1.316) with
fixed Stainless SDK and runtime versions from 2.1.282 (0.112.1, v26.3.0). The real
2.1.316 build reports 0.128.0 and v26.12.1, so the gateway described a client that
never existed, and the gap grew with every release (sub2api #8440).

Pinning to a reviewed list instead was rejected: Anthropic rejects new models from
older Claude Code versions (`claude_code_version_too_old`, sub2api #6481/#7532), and
Google enforces the same for Antigravity, which already verifies each build.

## What Changes

- A newer stable release is adopted only after its published Linux x64 npm package
  was downloaded, matched to the registry's integrity hash, and its native binary
  scanned for the SDK and runtime versions. The build is never executed.
- Builds verified at review (2.1.282 and 2.1.316) ship with the code; later ones are
  stored in `claude_client_builds`.
- Requests send the CLI, SDK and runtime versions of one verified build.
- Pins select a verified build; the dashboard lists verified builds with their values.
- A failed verification keeps the last verified version and retries in 15 minutes.
- The migration resets a discovered or pinned version without a verified build.

## Impact

- Backend: `app/modules/claude/version.py`, `profile.py`, `dispatch.py`; new table and migration.
- Frontend: Claude version controls.
- About 150 MB download per adopted release, never at request time.
