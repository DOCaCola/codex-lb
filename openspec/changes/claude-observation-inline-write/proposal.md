# Write Claude Quota Observations Inline Without a Timeout

## Why

Quota observations from Claude response headers were written under a 0.5-second timeout. Under load, that
timeout cancelled the SQLite commit mid-flight. Reclaiming the wedged connection took about 5 seconds, so the
response stalled for 6.3 seconds and the observation was still lost. The bound was meant to protect the response
from database stalls, but cancelling a commit costs more than finishing it. Other request-path bookkeeping, such
as API-key usage reservations, already writes inline and is shielded from cancellation.

The references agree. agent-lb, sub2api and CLIProxyAPI write the observation inline without their own timeout
and log failures; opencodex updates memory synchronously. None of them cancels the write.

## What Changes

- The observation write runs inline to completion, without a timeout.
- Caller cancellation during the write is delivered once the write finishes.
- Write failures are still logged and never fail or retry inference.

## Impact

- Specs: `claude-accounts` (Live Claude quota observation). Supersedes the "short timeout" decision in the
  archived `claude-live-quota` design.
- Code: `record_headers` in `app/modules/claude/observations.py`.
