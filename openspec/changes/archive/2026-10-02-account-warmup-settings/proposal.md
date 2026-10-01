## Why
Codex dashboard cards carry a limit warm-up row (opt-in state, last attempt and an On/Off toggle). It is an account setting rather than live capacity, and it makes Codex cards the tallest provider card, so every card in the equal-height grid grows to fit it. The Accounts page already offers the toggle, but only as an action button without the last-attempt status.

## What Changes
- Dashboard Codex cards SHALL no longer show limit warm-up state, details or a toggle.
- The Accounts page account settings SHALL show limit warm-up as a labeled switch with the latest attempt status, window, model and time, replacing the Enable/Disable Warmup action button.
- The dashboard list view keeps its warm-up column.
- Dashboard cards SHALL follow the provider order used by the model list and Accounts page: Codex, Claude, then OpenRouter.
- Claude accounts SHALL be listed by name, matching OpenRouter.
- The user-facing name "Limit warm-up" reads as a verb next to its switch, and "Quota warm-up" is taken by the Quota Planner. The feature SHALL be labeled "Window warm-up", with a description of its actual effect: starting usage windows early so they reset sooner. Internal identifiers stay `limit_warmup`.

## Capabilities
### New Capabilities
### Modified Capabilities
- `frontend-architecture`: per-account warm-up controls move from dashboard cards to Accounts page settings; dashboard card provider order.
- `claude-accounts`: stable account list order.

## Impact
Dashboard account cards, Accounts page account actions, translations, the Claude account repository and tests. The equal-height grid shrinks to the tallest remaining card.
