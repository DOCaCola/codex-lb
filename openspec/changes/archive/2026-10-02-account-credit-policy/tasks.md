## Implementation
- [x] 1. Add `credit_policy` (`spend`/`never`) to accounts with a migration.
- [x] 2. Thread the policy through quota status derivation, selection, the usage updater and pooled credit headers.
- [x] 3. Carry the policy in the routing-availability snapshot and fence quota-blocked `never` accounts.
- [x] 4. Add `PUT /api/accounts/{id}/credit-policy`.
- [x] 5. Recheck routing availability before reusing an upstream websocket; retire unavailable sockets.
- [x] 6. Add the Accounts page credit policy control and translations.
## Verification
- [x] 7. Unit and integration tests for selection, updater enforcement and recovery, replica propagation, websocket fencing and pooled credits.
- [x] 8. Frontend tests, lint and typecheck.
- [x] 9. Validate the change.
