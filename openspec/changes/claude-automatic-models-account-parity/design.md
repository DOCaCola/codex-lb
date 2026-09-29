# Design

## Context

See proposal.md. Read-only production discovery on 2026-09-29 returned HTTP200 and token capabilities for all models, including Opus5 at 1000000/128000 and Haiku4.5 at 200000/64000. No inference or credential rotation was performed. OmniRoute c3c540da reads max_input_tokens/max_tokens from authenticated discovery; OpenCodex 8a005dd98 supplements discovery with maintained metadata; CLIProxyAPI d33f63f defaults missing request budgets from its registry. These are source observations, not proof of all account entitlements.

## Goals / Non-Goals

Automatic account-authenticated token limits and shared visual primitives, with per-account policy delegated to the existing scheduler. No production deployment, new provider-wide strategy, protocol feature expansion or OAuth identity changes.

## Decisions

- Preserve discovered input/output limits and resolve absent fields using an explicit model registry. Unknown models lacking either limit remain unselectable, with a visible explanation; never invent a generic budget. Discovery values win. Selections retain model IDs only; mutation rejects obsolete override fields.
- Persist effective limits in existing projected model rows. Native explicit budgets remain validated against model capabilities; omitted Responses budgets use min(64000, resolved output maximum). Advertise 90% auto-compaction and 95% effective context separately from the full discovered context. Remove the 8192 runtime fallback.
- Migrate historical selection JSON to IDs only and invalidate old catalog freshness/projections, forcing rediscovery before dispatch uses former manual values. Do not keep compatibility overrides.
- Add Claude-only routing_policy storage, default normal. Feed this to the existing shared candidate type. Preserve its strategy-specific semantics: policies do not supersede hard owners/affinity or special drain/single-account strategies.
- Share Codex card/list/detail quota primitives and routing control/badge. Use the same remaining-percentage/date formatting and information hierarchy; retain Claude stale/unknown/overshoot diagnostics without displaying fictitious OpenAI workspace, credits or warmup fields.

## Risks / Trade-offs

- Missing upstream metadata → explicit maintained entries for known models; unresolved models stay disabled.
- Existing projections contain manual limits → migration disables them until successful metadata refresh; selected IDs survive.
- Shared component changes → verify existing Codex tests along with Claude views and read-only behavior.

## Migration Plan

Single-head migration adds normal routing policy and removes historical manual fields, invalidating old projected budgets. Downgrade removes routing policy; removed operator overrides are intentionally not recoverable. Refresh after upgrade resolves selected models automatically. No deployment in this task.
