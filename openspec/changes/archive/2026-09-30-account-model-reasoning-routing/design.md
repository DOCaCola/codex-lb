# Design

## Context

Model membership is persisted independently of live eligibility. Native warm transports use a replicated routing snapshot. Provider catalogs project source-model rows. See proposal.md for motivation.

## Goals / Non-Goals

Goals: restrict selection by requested reasoning while preserving defaults, account priority, ownership and saved membership. Non-goals: payload effort rewriting, native image eligibility changes, deployment.

## Decisions

- Store reasoning restrictions separately from membership, as model-to-nonempty-efforts maps. Missing keys mean unrestricted, including future efforts. Native accounts get one JSON column; provider typed states hold the same policy.
- Resolve omitted effort from current model metadata. An unresolved default cannot satisfy an explicit restriction; unrestricted routing is unchanged.
- Treat explicit `none` as a requested effort, never as omission. Existing wire normalization stays intact; internal provenance preserves a requested `minimal` for operator eligibility before an existing normalization changes the wire value. API-key enforced effort supersedes that provenance.
- Native Codex clients send client-side `ultra` as `max`. Native configuration exposes deduplicated wire efforts and rejects newly added `ultra` restrictions; operators select `max`. The server cannot distinguish client-side delegation modes that have the same wire effort.
- Filter eligibility before scheduling, revalidate warm sessions, and keep source-owned denials from falling through to native accounts.
- Retain saved IDs regardless of entitlement. Present live availability separately rather than deleting preferences.
- Validate membership and reasoning atomically against the original saved IDs. Reasoning-only saved missing IDs remain editable and reselectable, but do not grant selected-mode membership. Provider all mode retains disabled ownership claims for vanished configured IDs to prevent native-account fallthrough.
- Use shared checkbox-dropdown reasoning controls and dialog-local draft state, saved atomically with model mode. Provider image selections remain separate.

## Risks / Trade-offs

- Cached native account objects → propagate policy through routing snapshots and test refresh races/reuse.
- Owned continuations → fail closed when restricted, never force rebind.
- Missing provider reasoning metadata → unrestricted routing stays unchanged; explicitly restricted omitted-effort requests fail closed.

## Migration Plan

Add native JSON policy column with empty-map default. Existing accounts remain unrestricted. Downgrade removes only that column; provider policies live in existing JSON state.
