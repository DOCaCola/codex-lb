# Account model controls context

The account action sections share routing policy and a model dialog. The All
models switch is inside the conversation-model dialog. Codex defaults to All,
preserving pre-upgrade routing; Claude and
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

Reasoning restrictions are independent of membership: a missing model key means
all supported efforts, including future additions; an explicit key holds a
nonempty effort list. Eligibility filters the account pool before priority and
affinity. For example, a burn-first account allowing only medium cannot serve a
high request while an eligible normal account can. Explicit `none` means no
reasoning and is not replaced with the default. An omitted effort uses the
advertised default; if that default is unknown, a restricted account cannot
satisfy the request. No effort is silently substituted to make routing succeed.

Existing wire normalization is separate from operator policy. Routing retains
the original `minimal` when an existing transport rule normalizes it; API-key
enforced effort replaces the request's policy effort. Native Codex client-side
`ultra` arrives as `max`, so native account configuration exposes `max` rather
than advertising a server-side distinction it cannot enforce.

Mode, membership and reasoning are dialog-local drafts committed in one account
update; cancellation discards all three. Saved missing IDs, including IDs retained
only in the reasoning map, remain editable and can be reselected. Retained policy
does not itself grant selected-mode membership or upstream availability. Provider
all mode keeps disabled claims for unavailable configured models so they cannot
accidentally fall through to native accounts. Returning catalog availability
restores the existing selections and restrictions without another edit.

The native-account migration backfills existing rows with an empty policy map.
Provider policy uses the existing typed JSON account state; client catalogs omit
internal account allowlists. There are no new deployment settings.

These controls do not curate native image entitlements: native image endpoints
keep their existing model-neutral account selection. OpenRouter image models
stay in their separate explicit selection dialog, even with All enabled.

OpenRouter policy ranks usable burn_first accounts before normal before preserve,
rotating inside that priority pool. Cooling-down or excluded accounts cannot win
priority. This prepaid provider has no fabricated subscription quota strategy.
