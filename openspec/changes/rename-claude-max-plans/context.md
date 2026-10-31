# Context

Sources (checked 2026-10-31): Anthropic's announcement on X (2026-10-30), quoted
by Windows Report, daily.dev and Digg. Max 5x became Max ($100, 5x Pro on both
windows); Max 20x became Ultra ($200, 10x Pro weekly, 20x Pro per five hours until
the five-hour limit is removed for verified accounts). Weekly limits are unchanged,
so codex-lb's weekly weight of 20 for the former Max 20x was always a factor of two
too high.

Anthropic has not published new tier identifiers. Bootstrap and imported
credentials still report `default_claude_max_5x`/`default_claude_max_20x`; the
resolver also accepts `max` and `ultra` so a later identifier change keeps the
labels correct.

Production on 2026-10-31 held 59,034 request-log rows recorded as `max_5x` and
none as `max_20x` or a bare `max`, so the downgrade's reverse mapping is exact
for the deployed data.
