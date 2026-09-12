# Harden fork compaction

## Why
Source summarization must not report success after silently losing retained history. Subscription overflow must use the same compaction protocol as direct source routing.

## What Changes
- Reject unresolved continuation handles and unreadable compaction checkpoints before source dispatch.
- Route terminal overflow compaction through synthetic compaction with existing claim ownership and accounting.
- Preserve explicit item-reference identities for unstored requests.
- Repair fork test typing and verify regression coverage.

## Impact
Model-source routing and Responses compatibility; no deployment or configuration changes.
