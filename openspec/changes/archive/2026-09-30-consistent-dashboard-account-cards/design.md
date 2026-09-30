# Context

Codex cards are nested inside an animation wrapper; Claude/OpenRouter surfaces are direct grid children. The wrapper stretches but the nested Codex surface does not. Provider content and optional identity lines determine different natural heights. Footer spacing is duplicated across providers.

# Goals / Non-Goals

- Goal: one shared header/body/action layout and responsive grid sizing for all provider dashboard cards.
- Goal: preserve relevant provider observations and existing permissions/actions.
- Non-goals: unify quota units, fabricate provider fields, change routing or redesign account details/list rows.

# Decisions

AccountCardSurface owns typed title/subtitle/optional description/status/actions slots, a content body, and common footer styling. Its flexible body anchors actions at the bottom. A shared minimum header space accommodates the optional third identity line without fixing or clipping card height. Common notice/action primitives retain the existing Codex visual language.

All provider cards receive the same animated, flexible grid-item wrapper. Multi-column grids use equal intrinsic row sizes, determined by the largest rendered card; single-column layouts use natural heights. Cards and wrappers have minimum width zero. There is no height cap or inner scrollbar.

Codex and Claude card quotas reuse a shared quota-grid component: one available window uses one column; multiple windows use two columns at all card widths. Claude detail/list responsiveness remains unchanged. OpenRouter preserves dollar metrics and uncapped/unknown distinctions.

# Risks / Trade-offs

Providers with fewer metrics have whitespace above their footer on multi-column screens. This is intentional alignment, not empty fabricated metrics. Long action groups can wrap and the intrinsic grid grows to accommodate them. Small-screen cards retain natural heights rather than importing desktop whitespace.

# Verification

Component coverage preserves provider values, privacy, action semantics and shared anatomy. Browser coverage measures all card bounds, header/body/footer alignment, quota columns, containment and lack of clipping at desktop, tablet and mobile widths, with screenshots in both themes.
