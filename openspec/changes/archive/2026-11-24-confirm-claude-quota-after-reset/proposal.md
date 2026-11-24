## Why

After a Claude account's five-hour window reset, the dashboard kept showing it at 0% remaining until the next idle usage read or a manual refresh. On 2026-11-20 the window reached 100% at 20:36 UTC and reset at 21:10. The scheduled reads at 20:51 and 21:06 still saw 100%, and the next would have run at 21:21; the manual refresh at 21:14 cleared it. Routing was not affected: a passed reset already stops blocking (a request after the 16:10 reset went through at 16:13 without a read).

Two gaps caused this. An exhausted account receives no replies, so no headers report the reset, and usage reads ignore the known deadline and wait for the 15-minute idle interval. Separately, a window whose reset had passed was marked unknown but still carried its pre-reset utilization, so the card showed 0% remaining next to a past reset time, and capacity ranking counted the window as 100% used.

The references treat a passed reset the same way: OpenCodex drops expired measurements to unknown, and our Codex accounts show an elapsed short window as absent.

## What Changes

- A window whose reset deadline passed reports unknown utilization and no reset deadline until a new observation arrives.
- Scheduled usage reads also become due once a known reset deadline passes after the window's latest reading; a read completed after the deadline satisfies it. Existing failure and 429 backoff still applies.

## Impact

- Specs: `claude-accounts`.
- Code: `app/modules/claude/quota.py`, `app/modules/claude/metadata.py`, and their unit tests.
- One extra usage read per passed reset deadline; no settings, schema or client changes.

