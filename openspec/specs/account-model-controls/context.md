# Account model controls context

The account action sections share an All models switch, routing policy and model
dialog. Codex defaults to All, preserving pre-upgrade routing; Claude and
OpenRouter default to selected mode. All mode means every eligible conversation
model, not bypassing discovery, plan, quota or client-key restrictions.

Switching modes does not erase curated IDs or provider overrides. For example,
selecting only gpt-6-astra, switching All on, then off restores that selection.
An empty selection in selected mode disables conversation routing on that account.
Removed catalog entries stay visible as unavailable saved selections and can be
removed from the dialog. Codex models derive from the native registry and its
account/plan evidence, never from external-provider catalogs.

Restrictions apply to fresh selection and warm HTTP/WebSocket sessions. Updates
invalidate selection inputs and propagate account-routing snapshots to other
replicas; local overlays cover the interval before snapshot refresh. A restricted
account cannot retain a model through affinity. Strict conversation ownership
still fails closed rather than silently moving upstream-owned history.

These controls do not curate native image entitlements: native image endpoints
keep their existing model-neutral account selection. OpenRouter image models
stay in their separate explicit selection dialog, even with All enabled.

OpenRouter policy ranks usable burn_first accounts before normal before preserve,
rotating inside that priority pool. Cooling-down or excluded accounts cannot win
priority. This prepaid provider has no fabricated subscription quota strategy.
