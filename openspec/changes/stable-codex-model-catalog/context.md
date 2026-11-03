# Evidence

Production, 2026-11-02 UTC:

- 18:04:28 DOCa Plus (the only plus account) reached its quota and became `quota_exceeded`.
- 18:04:48 the refresh logged `plans=1`; the persisted snapshot hash changed from `c3b8cd95` to `cd3a32ad`.
- 19:35:00 the account was active again, `plans=2`, and the hash returned to `c3b8cd95`.
- 19:35:14 and 19:35:41 two Claude conversations missed their whole cache; the miss logger attributed one to `tools=changed:CollaborationSpawnAgent`.
- Conversation `01a0e444` then logged `claude_thinking_binding ... prefix_binding_mismatch` about 77 times until 22:19.

Cause: `_group_by_plan` in `model_refresh_scheduler.py` kept only `ACTIVE`
accounts, and the registry correctly drops the catalog of accounts that leave
the account set it is given.

Codex (`codex-rs/core/src/tools/handlers/multi_agents_spec.rs`) lists up to five
picker-visible models, with descriptions, efforts and service tiers, in the
`spawn_agent` tool description. The client sorts by priority, so ties keep the
order we serve.

Reference: OpenCodex `structure/catalog.md` at `684ad75d` (inspected 2026-11-03)
states that the published catalog must not depend on availability, credentials,
account state, quota or health.
