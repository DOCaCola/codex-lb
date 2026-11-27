## Why

On 2026-11-23 the Plus account reported its 5-hour window at 100% from 13:35 to 15:37 UTC. In that time seven composer predictions from the same Codex session failed with `previous_response_owner_unavailable`, for example `01a208b3` at 13:58:43.

Each prediction starts a new thread under the parent chat's session. With no thread row yet, selection takes the session's account as a seed preference. That account was the exhausted Plus account. The seed path checks only overload backoff, not usage exhaustion; the existing-row path releases an exhausted owner. Upstream rejected each request. The request body carries encrypted reasoning, so it was bound to the account it had been dispatched to, and the replay failed closed. The client's own retry then succeeded on the Pro account.

The binding is intended: a non-neutral body must not cross accounts inside the proxy. The defect is dispatching to an account that reports a used-up window while a sibling has quota left.

## What Changes

- A session seed preference for a new thread row is declined when the preferred account reports a primary or secondary window at 100% or more and the pool's best candidate is a different, non-exhausted account. Normal selection then chooses the account. This uses the same rule and evidence as the release of an exhausted existing owner.
- When every candidate is exhausted, or the preferred account is rate-limited (handled by selection itself), the preference is kept.

## Impact

- Spec: `sticky-session-operations`.
- Code: `app/modules/proxy/_load_balancer/sticky_selection.py`.
- No settings, schema or client changes. Dispatch-owner binding is unchanged.
