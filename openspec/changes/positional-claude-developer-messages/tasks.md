# Tasks

## 1. Projection

- [x] 1.1 Keep leading developer/system messages in the system prompt and place later ones after the next user turn as system turns, or as a closing `<system-reminder>` for models without system turns; verify tool-result, deferred, continuation-tail and prefix-stability cases.
- [x] 1.2 Send the mid-conversation beta whenever system turns are present; verify coexistence with relocated instructions.

## 2. Recovery

- [x] 2.1 Skip system turns in the open tool turn walk; verify the open turn stays signed behind a trailing system turn.

## 3. Verification

- [x] 3.1 Run Claude regressions, lint, format, type and strict spec validation; do not deploy.
