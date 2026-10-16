# Tasks

## 1. Implementation

- [x] 1.1 `authenticate_replay`: only active hosted search pins the account and model; every authenticated block sets
  the preferred account.
- [x] 1.2 `ClaudeReplay.project`: forward signed and redacted thinking verbatim on any route; compaction converts only
  completed thinking from another route.
- [x] 1.3 Typed codes and input indices for signed-history errors in `opaque.py`, `replay.py` and
  `chat_replay.py`; remove `ClaudeOpaqueState.decode` and restore through `authenticate`.

## 2. Verification

- [x] 2.1 Unit tests: completed and active thinking unchanged across account and model, active thinking never pins,
  active search still bound with typed errors, compaction conversion and active verbatim forwarding.
- [x] 2.2 Integration tests: completed thinking forwarded across account and model switches; an active Opus thinking
  turn resumed on another model dispatches with the signed block.
