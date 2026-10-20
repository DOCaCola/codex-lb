# Tasks

## 1. Implementation

- [x] 1.1 Port upstream #2486/#2627: admit a hard owner pool's sole backed-off candidate; trigger it from the
  ownership flag, not from any narrowed pool.
- [x] 1.2 Add `owner_holds_no_upstream_state` to the affinity policy and pass it through selection; a hard sticky row
  takes the soft path when it is set.
- [x] 1.3 In the HTTP bridge, a durable row without a response anchor, for a request without `previous_response_id`, sets the flag and
  supplies neither a preferred nor a required account.
- [x] 1.4 Revert `810c50cf0`.

## 2. Verification

- [x] 2.1 Integration: a thread whose first turn failed after `response.created` retries on another account; fails without the
  fix with the production 502.
- [x] 2.2 Balancer: hard owner in backoff keeps the turn; a hard row without upstream state leaves a backed-off account
  and keeps a healthy one; a preferred account in backoff is not admitted.
- [x] 2.3 Unanchored fork rows start selection without a preferred account.
- [x] 2.4 HTTP bridge, balancer, overload-backoff, proxy-utils and owner-retirement suites, ruff, format and ty pass.
