# Design

## Context

The top-consumer query groups request logs by key/model and unions rankings by
requests and billable tokens. It already uses the correct two-hour/deletion and
warmup filters. Costs and request coverage are computed elsewhere by shared SQL
expressions. Provider dashboard cards already reuse AccountCardSurface.

## Goals / Non-Goals

Goals: add cost without another fetch/query per consumer and simplify subtitles.
Non-goals: deriving costs from weekly quota credits, new pricing, changing rank
order, removing model selection controls or deploying.

## Decisions

- Aggregate shared cost expressions alongside existing model groups, sum across
  models, then deduplicate candidate totals using the same MAX strategy as usage.
- Carry one typed cost-coverage value, whose known subtotal is the cost source of
  truth, through the existing overview/projections attribution response.
- Reuse compact cost formatting and put full coverage information in a tooltip.
  Add a narrow, right-aligned cost cell; use card-width container queries to
  wrap metric rows in narrow cards (including desktop side columns) so names
  and long amounts cannot force page overflow.
- Keep card subtitles as Plus / OpenRouter · Paid / Claude · Pro when a Claude
  subscription plan is available. Preserve concurrent subscription discovery.
  Optional Codex ID
  separators also use ·; account model-selection controls remain unchanged.

## Risks / Trade-offs

- Mixed unknown/free data → shared coverage classification and regression cases.
- Candidate union double counting → retain MAX deduplication after grouped sums.
- Added width → real browser checks at narrow/desktop widths with long amounts.

## Migration Plan

Deploy backend and dashboard together; no migration or configuration change.
