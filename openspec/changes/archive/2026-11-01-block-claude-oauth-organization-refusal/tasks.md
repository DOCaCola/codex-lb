## 1. Refusal handling

- [x] 1.1 Classify the whole organization OAuth refusal and record it on the sending credential generation.
- [x] 1.2 Fail over from the refused account within the request send budget.
- [x] 1.3 Exclude blocked accounts from routing and fail locally when only blocked accounts remain.

## 2. Recovery

- [x] 2.1 Clear the block on a later successful usage or subscription refresh and on reconnect.

## 3. Presentation

- [x] 3.1 Show blocked accounts as deactivated with a "Subscription inactive" notice.

## 4. Verification

- [x] 4.1 Cover failover, local failure, unrelated 403s, refresh ordering and stale generations.
