# Design

## Context

See proposal.md. ModelSource already owns generic provider discovery, API-key source restrictions, admission and request accounting. Native Account is OpenAI-specific; Claude must not populate fake id-token fields. Research is recorded in ../../../../../../claude-integration-design.tmp.md and repository AGENTS.md references.

## Goals / Non-Goals

Goals: separate Claude domain with reusable provider dispatch, durable auth state and preserved native protocol; full local regression coverage.

Non-goals: production rollout, live credential use, automatic server-local credential extraction, cookie/setup-token modes, executing Claude CLI, fabricated billing fingerprints, silent paid fallback, guarantees of subscription eligibility.

## Decisions

- Extend ModelSource with a Claude-owned credential/state row. Separate encrypted credential bundle from public catalog/usage state. Reuse source permissions and dispatch ownership rather than a parallel account authorization mechanism.
- Coordinate rotating grants with a database compare-and-swap durable refresh intent and generation. Commit intent before dispatch. Terminal invalidation requires reauth, definitive transient HTTP rejection clears intent with backoff, ambiguous transport outcomes retain uncertain state. Do not use a process lock as cross-worker proof.
- Use explicit credential-file validation and single-use persisted PKCE enrollment. Do not infer account identity from mutable access tokens or user-provided display names.
- Native Messages forwarding preserves semantic body and protocol metadata; translated Responses is a distinct explicit adapter. Never identify trusted callers from a spoofable UA. Reuse source admission, stream lifecycle, replay and compaction; preserve account ownership of signed state.
- Use bounded authenticated catalog pagination and atomic replacement. Operator selections survive refresh and new models stay disabled. Display provider quotas without guessing total capacity or entitlement from percentages.
- Store shared version-discovery metadata independently of accounts. Leader scheduler performs a bounded conditional GitHub stable-release lookup daily; manual pin wins and each dispatch snapshots identity once. Baseline is 2.1.282; version following is not full-profile verification.
- Preserve native/translated eligibility errors. Sub2API supplies architecture/cache/version lessons, OpenCodex adapter/refresh lessons, OmniRoute explicit import lessons, CLIProxyAPI profile/terminal regression lessons. No wholesale source copying.
- Apply a versioned OAuth request profile after protocol conversion, keeping the original logical history separate. Recognized native Claude Code traffic preserves its body; recognition is a compatibility hint, never authentication. Translated traffic uses the Claude Code identity and non-strict instruction relocation: verified modern models use mid-conversation system blocks; legacy models use explicit user reminders. Unknown models require an explicit supported placement policy rather than optimistic role support. Preserve caller block contents/cache markers and tool adjacency; reject layout changes involving account-bound server artifacts unless supported. Do not delete identity paragraphs or obfuscate arbitrary text.
- Separate management, Messages and count-tokens headers. CLI version, SDK baseline and profile revision are independent. Stable session IDs bind account and conversation, never access tokens; request IDs are fresh. Only allowlisted native metadata is forwarded and caller authorization is always replaced. Model-dependent betas accompany actual features; version discovery does not imply profile qualification.

## Risks / Trade-offs

- OAuth upstream acceptance and included-plan eligibility are unverified locally → keep release qualification explicit and run authorized isolated acceptance before production.
- Rotated token response lost after dispatch → require reauthentication rather than unsafe replay.
- Provider model features evolve → preserve native extension fields; explicit adapter validation and regression fixtures.
- Long thinking → transport pings retained, no fabricated semantic progress.

## Migration Plan

Add a single-head additive migration; test upgrade/downgrade on an isolated database. With no Claude account, existing routes remain unchanged. Do not deploy during this work. Rollback of an installation with Claude accounts requires disabling/removing those accounts before schema rollback; credentials are never exported automatically.
