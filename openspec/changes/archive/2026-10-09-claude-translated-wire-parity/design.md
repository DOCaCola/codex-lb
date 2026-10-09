# Design

## Context

See proposal.md and the isolated lab's REPORT.md / REFERENCE-GAPS.md. Claude already has encrypted account/model/client/conversation-bound thinking and durable Responses continuation. Native caller-owned history must stay distinct from translated wire history.

## Goals / Non-Goals

**Goals:** restore default Codex tool compatibility, including safe search continuation; establish stable cache boundaries and coherent synthesized identity.

**Non-Goals:** billing fingerprints, cloned behavioral prompts, automatic paid fallback, deployment, or claiming live OAuth acceptance.

## Decisions

- Native versioned Anthropic search replaces live Responses declarations. Following the user's explicit choice of CLIProxyAPI behavior, external_web_access=false omits the declaration: normal conversation continues without cached or live search. Other unsupported options fail before dispatch. CLIProxyAPI is a structural reference, not copied code.
- Public search lifecycle and citations use Responses items/events. Genuine server search blocks are transported in an authenticated opaque reasoning carrier, which Codex already preserves, instead of relying on unknown fields in web_search_call. Its envelope includes the public search item ID; replay requires matching scoped state and never fabricates encrypted search results.
- Instruction projection for trusted translated replay runs deterministically from original logical history. Native third-party signed history retains its existing relocation restrictions.
- Translated requests receive at most three 5m ephemeral breakpoints: final stable system block and the latest two cacheable user turns (or tools when no system exists). Explicit native markers and reasoning/server-tool blocks are not rewritten. Choosing 5m avoids silently selecting a more expensive cache-write tier; no automatic caching field is mixed in.
- Synthesized metadata uses a stable local source/client device hash and existing conversation-scoped session UUID. Provider account_uuid is explicitly empty because the database stores a non-reversible identity fingerprint, not the provider UUID. Never derive a fake provider UUID or add a network lookup to every request.
- Platform/architecture headers reflect runtime; synthesize the observed browser-access header but not the absent stream-helper header. Preserve recognized native helper hints. Keep immutable reviewed SDK/runtime constants alongside the separately discovered CLI version.

## Risks / Trade-offs

- Opaque state must survive actual client replay → exercise the bundled app-server, not only helper tests.
- Native web-search results bind account and conversation → use authenticated envelopes and reject lost/mismatched state before dispatch; test paused owner and changed scope.
- Search/citation stream ordering → test streamed and collected Responses, including incomplete/error cases.
- References disagree on billing identity requirements → do not fabricate attribution; live provider acceptance remains unqualified.

## Migration Plan

No schema or configuration migration. No deployment in this task. Existing signed-thinking envelopes remain valid; new search envelopes require this version to replay.
