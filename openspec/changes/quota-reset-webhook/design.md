## Architecture

Use authoritative usage snapshots only, with fetch-start timestamps to discard
out-of-order completions. Keep per-account/window baselines and outbox transitions
in the usage transaction. Serialize configuration/baseline updates using a database
row lock (SQLite write lock); do not use telemetry's relaxed commit durability when
notifications are enabled. Missing windows do not become zero. First observations,
plan/duration/identity changes and pre-enable fetches establish no reset event.

Scheduled resets require crossing the old deadline with corroborating quota data.
Unexpected drops require at least five percentage points before that deadline;
rolling deadline creep is excluded. These observations do not prove provider cause.
Mark reset-credit intent at the shared consume boundary before dispatch, suppressing
notifications for ten minutes even if the result is ambiguous. This conservatively
avoids labeling a known redemption as a surprise. Workspace-shared IDs suppress all
matching seats. No paid redemption or generation is triggered by the observer.

Persist unique event IDs, not reset-deadline-only keys. Advancing the baseline in
the same transaction prevents duplicate transitions but permits later same-deadline
resets after consumption. Single-event POSTs, no consolidation. Delivery claims
use leases and configuration generations. Configuration changes cancel pending
events; an already in-flight HTTP request cannot be recalled. Retries retain ID
and payload, at most four attempts within fifteen minutes. Seven-day retention
and a 1000-pending cap bound storage; overflow is visible in sanitized logs.

Allow HTTP and HTTPS destinations with normal DNS resolution, including private
and loopback addresses. Do not follow redirects; retain HTTPS certificate checking.
No environment proxy, auth headers or cookies. URL and optional HMAC secret encrypted
at rest and never returned. HMAC covers timestamp + dot + exact JSON bytes; receivers
deduplicate event IDs and apply a timestamp replay window.

UI lives in Settings, with admin-only mutation/test, read-only status, filters and
explicit secret replacement/removal. Test delivery uses the same queue and sender.
Borrow behavior from OpenCodex detection and OmniRoute delivery research without
copying source. No live destination is contacted during automated verification.
