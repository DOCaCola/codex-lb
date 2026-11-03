# Design

## Context
See proposal.md and context.md for the incident and reference evidence. Metadata
refresh already serializes state publication through the account version and
credential generation. Refusals use the same account lock and persist separate
window restrictions.

## Goals / Non-Goals
Recover routing during the existing successful usage refresh transaction. No new
polling, reset grants, schema migration or inference replay is required.

## Decisions
Capture persisted restrictions while claiming the usage refresh, before releasing
the transaction for network I/O. On accepted publication, compare current
restrictions with that snapshot and remove only matching evidence for explicitly
available windows. Existing effective-usage projection excludes readings displaced
by newer inference headers or reset barriers. This avoids an additional persisted
recovery generation and keeps usage publication and cooldown recovery atomic.

An unconditional cooldown deletion would erase entitlement and concurrent refusal
evidence. A timestamp-only comparison would confuse inference start order with
refusal arrival order. Exact captured evidence preserves both distinctions.

## Risks / Trade-offs
A missing or expired reading cannot establish recovery, so its restriction remains.
A refusal received during or after refresh remains eligible to block routing.
These cases recover on subsequent authoritative readings or deadline expiry.

## Migration Plan
Deploy normally. Existing named restrictions participate on the next successful
manual or scheduled usage read. Unknown legacy restrictions retain their deadline.
Rollback uses the retained prior application image; no database migration occurs.
