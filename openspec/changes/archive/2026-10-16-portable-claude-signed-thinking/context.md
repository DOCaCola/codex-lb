# Context

## Incident

- Request `ws_src_1de61b35f43948dc9b10f0ceeddacf59`, 2026-10-16 12:32:46 UTC, Windows Codex, conversation
  `01a0e444-cbc2-77f0-9741-8d15819ba5f3`. Rejected before account selection; no request log row, no upstream call.
- The previous Opus 5.5 steps (12:32:02, 12:32:07) ended in `tool_use`. Under multi-agent v2 Codex sends
  `<turn_aborted>` as a developer message, so the stopped turn stayed active for the replay classifier.

## Anthropic contract (platform.claude.com, preserved-thinking and thinking guides, read 2026-10-16)

- Model switches: keep passing thinking blocks unchanged; a block the target cannot read is dropped without error or
  billing. Sonnet 5.5 cannot read Opus 5.5 blocks, so an Opus-to-Sonnet switch runs without the earlier reasoning;
  Opus 5.5 reads Sonnet 5.5 blocks, and switching back reads both again.
- Account binding: Sonnet 5.5 and Haiku 5.5 blocks are read only on the producing (or a linked) account; elsewhere they
  are dropped silently. Blocks from other models are portable across accounts. This is why the producer stays a
  routing preference.
- Prefix check (default for accounts created on or after 2026-08-31 on Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5):
  editing `system`, `tools` or earlier messages invalidates later blocks with a 400. Removing blocks from the start,
  the end, or all of them is valid; removing one from the middle, or putting back a removed block, is not. The previous
  omission policy did both on a switch back.
- Documented recovery: retry once with `drop_block` (beta header) or remove all thinking once, and log it. Our
  existing recovery removes historical thinking while protecting the open tool cycle and logs
  `claude_signature_recovery`; it is unchanged.

## References

- CLIProxyAPI `internal/signature/provider_compatibility.go` (`claudeCompatibleSignatureReason`): a Claude signature
  is valid for any Claude target.
- OmniRoute `open-sse/handlers/chatCore/passthroughHelpers.ts`: forwards thinking verbatim; after a signature 400 it
  strips historical thinking, protecting the open `tool_use`, and retries once. Issue #2454: an earlier redaction
  attempt broke tool loops and was reverted.
- sub2api `FilterThinkingBlocksForRetry`: forwards thinking; on a signature 400 retries with thinking as text.
- opencodex binds by destination and credential domain, not by model.
- None recognises `<turn_aborted>`; no change to the active-turn classifier is needed once thinking is portable.

## Design notes

- Only hosted search stays account/model-bound: its portability is not covered by the thinking documentation, and
  completed search already has a readable projection.
- Compaction keeps its text conversion for completed thinking from another route because the summary must read content
  Anthropic would otherwise drop. A conversion may still trigger the prefix 400 for later kept blocks; the existing
  compaction recovery converts the rest, as before.
- The Chat replay path keeps its retained-record integrity check and its text reconstruction on model change; only its
  errors gain codes.
