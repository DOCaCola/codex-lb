## Why

An Antigravity generation that ends with only thought parts is resent once on
the same account. The resend's projection started from the first attempt's
usage, so the usage reported to the client was the sum of both attempts. Codex
and Chat clients read input tokens as the current context size, so after a
retry they saw roughly twice the real context and could compact early.
opencodex issue #8877 reports the same defect for its Claude continuation
guard.

The summed figure was also the only billing record. When both attempts came
back empty, no usage was recorded at all.

## What Changes

- The resend starts with fresh usage, so the client sees the final attempt's
  usage only.
- The transport keeps the discarded attempt's usage and records the sum of both
  attempts for billing, including when the retry is also empty.
- Usage carried across search rounds of one response is unchanged.

## Impact

- `app/modules/antigravity/transport.py`, `responses.py`, `inference.py`.
- Tests: `tests/integration/test_antigravity_accounts.py`,
  `tests/unit/test_antigravity_responses.py`.
- The Claude translation has no empty-completion retry, so it is unaffected.
