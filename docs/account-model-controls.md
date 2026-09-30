# Account model availability

Specification: [account model controls](../openspec/specs/account-model-controls/spec.md).
Details: [routing and continuity semantics](../openspec/specs/account-model-controls/context.md).

Each account detail has **All models** and a **Models** selection dialog. Codex
defaults to All; Claude and OpenRouter default to selected models. Switching
modes retains your saved choices. In All mode, newly discovered eligible
conversation models become available automatically. Upstream and client-key
permissions still apply.

For Codex, switch All off and choose native models in **Models** to restrict an
account. Selecting none disables its conversation models. Existing connections
cannot bypass the restriction, and upstream-owned conversations do not silently
move to another account. Native image routing remains unchanged. OpenRouter image
models are separately selected in **Image models**, regardless of All mode.
