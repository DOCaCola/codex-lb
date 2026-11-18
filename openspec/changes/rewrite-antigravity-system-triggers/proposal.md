## Why

Cloud Code answers some system-instruction sentences with an immediate `429 RESOURCE_EXHAUSTED` that carries no quota or retry details, even when the account has quota left. Reporters isolated each trigger in controlled tests: the same sentence in user messages or tool descriptions passes, and a neutral rewrite of it returns 200 on the original request (CLIProxyAPI #7428, #7545, #7553, #7627; OmniRoute #10420).

Our adapter still hides a fixed word list by inserting a zero-width space. Google now recognizes that obfuscation, as well as the U+034F variant (CLIProxyAPI #7428, #7545). The list also misses the trigger that affects us most: every current Codex model prompt opens with "You are Codex, … based on GPT-5/6.", and routed models inherit it. CLIProxyAPI's maintainers attribute the Nov 14–15 wave of `TOS_VIOLATION` suspensions to this prompt filtering (#7552), so sending flagged text is an account risk as well as a failure.

## What Changes

- Remove the zero-width obfuscation and its word list.
- Rewrite known triggers in plain words, only in `systemInstruction`:
  - Codex identity sentence → "You are a helpful coding assistant." (CLIProxyAPI's documented replacement).
  - Claude Code and Agent SDK identity lines are removed (OmniRoute).
  - Claude Code's role sentence and dual-use security sentence take the neutral wording verified in CLIProxyAPI #7627.
- Drop system parts left empty by a removal; omit `systemInstruction` when none remain.
- Log the names of the rules that fired, never the text.
- The OMP harness words (`system-directive`, `RFC 2119`, …) are no longer handled: no client we serve sends them, and obfuscating them no longer works.

## Impact

- Specs: `antigravity-accounts`.
- Code: `app/modules/antigravity/protocol.py`; tests `tests/unit/test_antigravity_protocol.py`.
- Unexplained 429s keep their existing handling: one same-account retry, never a walk across the pool.
