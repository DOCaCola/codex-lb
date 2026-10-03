# Project foreign reasoning of the active turn at Claude dispatch

## Why

On 2026-10-03 at 00:12:48 UTC, thread `01a0f38a` switched from GPT-6.1-Sol to Opus 5.5 right after Sol had issued a tool call. Sol's encrypted reasoning for that unfinished step was part of the active turn, so Claude dispatch failed with `nonportable_provider_history`, after about two minutes of compaction handoff. The conversation could only continue by switching back to Sol.

Claude can never read that ciphertext. Its only use would be continuing Sol's private reasoning, which no Claude request can do. Refusing the request preserves nothing. It only blocks the switch.

The references all drop foreign reasoning without regard to the active turn (inspected 2026-10-03):

- OpenCodex `249462bf5` drops foreign thinking blocks when the serving identity changes and still sends the `tool_use`.
- CLIProxyAPI `2044a01f4` removes incompatible thinking blocks so conversations can continue across Claude, GPT and Gemini.
- OmniRoute `23a114848` strips opaque reasoning fields when the target cannot use them.
- Sub2API `b8dece900` drops invalid signatures; on its Anthropic path it retries after a 400 with thinking turned into text.

None of them refuses the request, and none treats the active turn differently.

## What Changes

- Foreign encrypted reasoning in the active turn is projected like completed foreign reasoning: readable summary or reasoning text becomes assistant text in its original position, the ciphertext and lookup IDs are omitted, and an opaque-only item produces no Claude wire block.
- The same applies to complete-history compaction inside an open foreign tool loop.
- The `claude_foreign_history_projection` log line also counts active-turn items (`active=`).
- Unchanged: genuine Claude envelopes in the active turn stay bound to their original model and account; retained history keeps the original ciphertext; tool pairing is unchanged.

## Capabilities

### Modified Capabilities

- `claude-accounts`: foreign reasoning at Claude dispatch no longer fails for the active turn.

## Impact

- A mid-tool-step switch from an OpenAI model to Claude continues instead of failing. Claude sees the tool call, its result and any readable summary; it does not see the private reasoning it could not read anyway.
- `app/modules/claude/replay.py`, its unit and integration tests, and the compaction completeness tests.
