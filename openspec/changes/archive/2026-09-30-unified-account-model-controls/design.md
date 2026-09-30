# Design

## Context

See proposal.md. Provider accounts project selected catalogs into model sources; native accounts use upstream catalog evidence and cached load-balancer snapshots. Charts currently merge series timestamps, treating synthetic timestamps as unknown measured values.

## Goals / Non-Goals

Keep operator choices independent of upstream eligibility. Do not change quotas, server-resource ownership, image-backend selection, protocol adaptation, or production configuration.

## Decisions

- Store native all-model mode and retained model IDs on accounts. Provider mode lives in existing typed state; OpenRouter routing priority lives on its account row, mirroring Claude.
- All mode dynamically projects eligible conversation catalog entries. OpenRouter image selections stay explicit; selection overrides apply to selected catalog entries in either mode. Catalog removal retains disabled claims.
- Apply native operator restrictions separately from catalog/plan/quota gates, including warm-session compatibility. Invalidate account snapshots after mutation and consult fresh account state on transport reuse.
- Native image endpoints retain their existing model-neutral account selection; these controls curate conversation models, not image entitlements. Provider image choices remain in their separate explicit picker.
- Reuse shared model-mode controls/dialog layout. Claude moves its selection list into a dialog, keeps usage/monitoring/actions compact and places provider settings in an expandable section.
- Plot chart series on a shared numeric time axis with per-series samples rather than fabricating null samples from other series' timestamps. Preserve explicitly unknown samples and reset breaks.
- OpenRouter cooldown/exclusion gates precede manual policy; rotate within the highest-priority usable pool. No migration of conversation ownership.

## Risks / Trade-offs

- Catalog-wide mode increases advertised models → opt-in for providers, existing context caps retained.
- Account-bound continuations restricted by a new allowlist → fail eligibility explicitly rather than migrate ownership.
- Chart refactor affects native charts → regression tests for numeric spacing, unknown hours, plan gaps and sparse observations.

## Migration Plan

Add native mode/selection fields and OpenRouter policy in a single revision on the current head. Backfill native accounts to all and OpenRouter to normal; typed provider state defaults retain selected mode. Downgrade removes new columns only. No production upgrade in this task.
