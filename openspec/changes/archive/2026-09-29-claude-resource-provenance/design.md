# Design

Keep one-hour session affinity separate from observed server-tool origins.
Store scoped identifier hashes, source and timestamps, never history. Thirty-day
sliding retention is a local policy, not an upstream lifetime guarantee. Publish
no newly observed identifier before commit; persistence failure is terminal, not
a reason to regenerate. Use atomic insert/conflict checks and batched expiry
cleanup, without transactions spanning upstream I/O. Resolve complete input
provenance before credential refresh; authorization remains mandatory. Retention
refresh occurs after authorized admission, not on count_tokens or rejected lookup.

The initial resource class is native server_tool_use and matching server result
blocks. Files/containers require their own origin-capture paths and are explicitly
unsupported by this provenance contract. Unknown server block shapes fail closed.
No legacy origin backfill, arbitrary resource portability, signature stripping,
or changes to translated authenticated replay. Existing soft-affinity CAS remains;
resource-bound requests do not rewrite it. Delete-source cascades remove origins.

References: workspace claude-resource-continuity.tmp.md records the inspected
OpenCodex, Sub2API, CLIProxyAPI and OmniRoute revisions and bounded findings.
This ledger is a local design extension, not a claim of proven upstream migration.
