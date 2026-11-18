## Why

Cloud Code answers request-shape and policy refusals with a bare
`429 RESOURCE_EXHAUSTED`: no details, no `Retry-After`. We retried such a 429
once on the same account. opencodex measured that this replay is refused again,
because the same bytes meet the same refusal, and since #8897 it replays a
Google 429 only when the response carries retry evidence. Without evidence the
retry only spends another send.

Our classifier also treated any details-free 429 as unexplained, including ones
whose message names a short-lived limit ("per minute", "too many requests"),
which opencodex counts as evidence that a replay can succeed.

## What Changes

- A details-free 429 whose message names a transient limit or asks to try again
  later is a rate limit and follows the rate-limit recovery. The transient
  wording list matches opencodex's.
- A bare 429 without such wording is retried once on the same account only when
  Google sends a `Retry-After` header; otherwise it is reported immediately. It
  still never walks the pool, never marks quota and stays final to the client.

## Impact

- `app/modules/antigravity/classify.py`, `app/modules/antigravity/recovery.py`.
- Tests: `tests/unit/test_antigravity_classify.py`,
  `tests/unit/test_antigravity_recovery.py`,
  `tests/integration/test_antigravity_accounts.py`.
