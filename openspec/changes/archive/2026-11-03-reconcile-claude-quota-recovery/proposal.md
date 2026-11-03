# Recover Claude quota after allowance changes

Fresh usage after a Pro-to-Max upgrade can report available quota while a prior
inference 429 still blocks routing. Reconcile captured quota restrictions in the
existing metadata refresh transaction, for manual and scheduled reads.

## Scope

Recover named quota windows only. Preserve newer refusals, credential replacement,
unknown restrictions and entitlement restrictions. No additional polling or retries.
