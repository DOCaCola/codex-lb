# Design

## Context

The selector already evaluates eligibility within the authorized owner/model scope. Its owner-error branch precedes quota classification, so a known exhausted owner returns 503. Claude errors are serialized separately at native Messages and translated Responses boundaries; the source WebSocket bridge already forwards error bodies and a safe Retry-After header.

## Goals / Non-Goals

Goals: preserve strict account/model/client ownership and give every transport the same truthful refusal and retry timing.

Non-goals: rotate active signed history, drop history, change retry budgets, wait hours inside gateway requests, modify clients or deploy production.

## Decisions

- Classify quota-only candidates before constructing the owner refusal. Retain previous_response_owner_unavailable for hard owners so existing replay/recovery contracts do not change; only its quota-specific status and message change.
- Keep observed blocking windows in the eligibility result for content-free diagnostics. Unknown cooldown provenance remains non-quota and returns 503.
- Give Claude errors one typed public detail representation. Quota errors add existing OpenAI-compatible resets_at/resets_in_seconds fields only when the complete candidate recovery time is known. HTTP derives Retry-After from the same deadline; WebSocket forwarding retains the detail and allowlisted header.
- Use latest barrier per account, not the earliest quota window, and never advertise another account's recovery as the pinned owner's recovery.

## Risks / Trade-offs

- Clients may stop instead of sleeping on 429 → report the exact reset and do not promise automatic resumption.
- Mixed quota/auth/paused failures must not become rate limits → classify only pure quota eligibility and cover mixed/unknown states.
- Reactive recovery must retain actual upstream refusals → preserve last-error handling and regression suites.

## Reference evidence

Inspected 2026-10-01: OpenCodex ef0297f86c4540c7d757c8595170d66f9c584aec (AnthropicAccountCooldownError, adapter-dispatch.ts, ws-bridge.ts); CLIProxyAPI fd48ea6840f5572deb53aeb5657740937ac9daaa (selector.go model_cooldown, Claude credential cooldown tests); Agent LB c7f83276e4c8af0d7735adb6524fc68d34a97732 (anthropic_service.py quota eligibility). These support 429 and structured retry diagnostics, not proof that signed account state can safely migrate. Sub2API d6adebd22de00478cd021119ba755f37bcb94fb5 retains 503 on some generic selection failures; OmniRoute dbe703a0000b303cd7b1cf5879cb8740e5bfce71 maps 429 to rate_limit_error. Source inspection, not independent live qualification.
