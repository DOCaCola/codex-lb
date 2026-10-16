# Portable Native Checkpoint Handoff

## Why

On 16 Oct 17:32:47–17:33:00 UTC, seven checkpoint handoffs for a switch from GPT-6.1 Sol to Claude Opus 5.5 failed
locally with `previous_response_owner_unavailable`. Handoff generation was pinned to the account that produced the
native checkpoint, DOCa Plus, whose five-hour quota was exhausted from 17:27:48 until 19:40:10. Claude received
nothing. The error hid the quota cause, and the handoff rows carried no conversation ID.

The pin assumed native checkpoints are bound to their producing account. Production contradicts this. Over seven
days, 22 native conversations compacted on one account and then completed 17,613 turns on a different OpenAI account
with that checkpoint in their history, with no decryption rejection. At 17:29:21 an ordinary Sol turn of another
conversation failed on the same exhausted account and continued on another account eight seconds later.

None of the references binds encrypted Codex state to an account:

- CLIProxyAPI keys its Codex reasoning replay by session, so auth failover can preserve replay.
- opencodex treats a native compaction blob as readable by any OpenAI-operated destination.
- sub2api and OmniRoute fail over between OpenAI accounts with encrypted items intact and recover a rare rejection
  separately.
- frozen-codex-lb carries encrypted input to quota-failover replacements. A replacement's
  `invalid_encrypted_content` rejection reaches the client unchanged without harming that account's health.

## What Changes

- Handoff generation uses ordinary account selection for the checkpoint's model under the API key's current account
  restrictions. The producing account is no longer required, and the streaming path's `required_account_id` is removed.
- Account scope no longer gates handoff or cached summaries; the model restriction still does.
- A failed selection returns the same error as an ordinary native request instead of
  `previous_response_owner_unavailable`.
- Handoff request logs name the destination turn's conversation, without forwarding client affinity headers.
- An upstream `invalid_encrypted_content` rejection is a payload rejection: it surfaces unchanged and does not
  mutate the serving account's health.

## Capabilities

### Modified Capabilities

- `model-source-routing`: native checkpoint handoff generation is account-portable.
- `account-routing`: `invalid_encrypted_content` is an account-neutral payload rejection.

## Impact

- Code: `app/modules/proxy/api.py`, `app/modules/proxy/checkpoint_handoff.py`,
  `app/modules/proxy/_service/streaming/retry.py`, `app/modules/proxy/_service/streaming/helpers.py`.
- Stored provenance and summaries keep their format.
