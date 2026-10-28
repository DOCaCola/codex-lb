## Context and decisions

Use a shared `PlanBadge` with a typed palette of light/dark text, background, and border tokens. CSS selects the theme from the existing `.dark` ancestor and mixes the background with 8% text color on hover, matching the approved preview. Explicit hex tokens preserve the approved colors without depending on Tailwind palette revisions.

The palette covers free/slate, plus/emerald, prolite/orchid, pro/violet, team/sky, business/teal, enterprise/gold, edu/lime, max/orange, max_5x/rose, and max_20x/cobalt. Unknown is neutral. Recognized rate-limit metadata keys retain separate colors: guest/stone, go/cyan, free_workspace/indigo, education/olive, quorum/copper, k12/coral.

Labels remain the caller's responsibility so Claude translations and Codex formatting retain current behavior. Unknown upstream strings keep their existing labels and use the explicit neutral style. Null/blank snapshots remain an unbadged `--`. For example, Max 5× and Max 20× are rose and cobalt instead of sharing Pro's violet.

## Constraints and failure modes

Color complements the visible label; it is not the sole tier identifier. A new upstream plan must not appear to be Free. Account logo/chart colors remain separate. Browser checks must exercise built CSS in both themes because component-only tests cannot detect CSS cascade or hover contrast failures.
