## Why

On 2026-11-27 a conversation moved from Claude account A, whose weekly quota was exhausted, to account B. B wrote the whole prefix to its cache once, as expected. Its next compaction then converted all 68 completed Opus thinking blocks that A had produced into plain text. That rewrote the cached prefix, so 151k tokens missed the cache, and Anthropic dropped 16 of B's own later thinking blocks because their binding to the preceding content no longer matched (`prefix_binding_mismatch`).

The conversion was unnecessary. Anthropic's preserved-thinking guide (read 2026-10-16, recorded in `2026-10-16-portable-claude-signed-thinking`) says signed thinking is readable on any account, except Sonnet 5.5 and Haiku 5.5 thinking, which only the producing account can read. Another model cannot read it either. Compaction treated every account change as unreadable.

None of the references (opencodex, sub2api, CLIProxyAPI, OmniRoute) binds signed Claude thinking to an account; they forward it, and convert or strip only for model or provider changes or invalid signatures.

## What Changes

- Compaction converts completed thinking to readable text only when the selected route cannot read it: another model, or another account or identity generation for Sonnet 5.5 and Haiku 5.5 thinking.
- Readable thinking, including Opus thinking from another account, is forwarded signed and unchanged, which keeps the cached prefix and later bindings intact.
- Ordinary turns, search projection and active-state rules are unchanged.

## Impact

- Spec: `claude-accounts`.
- Code: `app/modules/claude/capabilities.py`, `app/modules/claude/replay.py`.
- No settings, schema or client changes.
