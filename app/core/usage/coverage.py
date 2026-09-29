"""Request-grain cost coverage shared by raw queries and durable folds."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, or_


@dataclass(frozen=True, slots=True)
class CostCoverage:
    known_cost_usd: float = 0.0
    priced_requests: int = 0
    unpriced_requests: int = 0
    unmetered_requests: int = 0
    coverage_unknown: bool = False

    @property
    def request_count(self) -> int:
        return self.priced_requests + self.unpriced_requests + self.unmetered_requests

    @property
    def complete(self) -> bool:
        return not self.coverage_unknown and self.unpriced_requests == 0 and self.unmetered_requests == 0

    def __add__(self, other: CostCoverage) -> CostCoverage:
        return CostCoverage(
            known_cost_usd=self.known_cost_usd + other.known_cost_usd,
            priced_requests=self.priced_requests + other.priced_requests,
            unpriced_requests=self.unpriced_requests + other.unpriced_requests,
            unmetered_requests=self.unmetered_requests + other.unmetered_requests,
            coverage_unknown=self.coverage_unknown or other.coverage_unknown,
        )


def request_cost_expressions(log):
    """SQL mirror of the request-level priced/unpriced/unmetered contract.

    A local refusal has no upstream status, attempt duration or observed usage.
    It cannot have generated billable output and stays outside coverage.
    """

    observed_usage = or_(log.input_tokens.is_not(None), log.output_tokens.is_not(None))
    attempted = or_(observed_usage, log.upstream_status_code.is_not(None), log.latency_ms.is_not(None))
    in_scope = (log.request_kind != "count_tokens") & or_(log.status.in_(("success", "ok")), attempted)
    legacy_claude_zero = (
        func.coalesce(log.model_source_kind == "claude", False) & log.cost_provenance.is_(None) & (log.cost_usd == 0)
    )
    known_cost = case((in_scope & ~legacy_claude_zero, log.cost_usd), else_=None)
    priced = in_scope & known_cost.is_not(None)
    unpriced = in_scope & known_cost.is_(None) & observed_usage
    unmetered = in_scope & known_cost.is_(None) & ~observed_usage
    return (
        func.coalesce(func.sum(known_cost), 0.0).label("known_cost_usd"),
        func.sum(case((priced, 1), else_=0)).label("priced_requests"),
        func.sum(case((unpriced, 1), else_=0)).label("unpriced_requests"),
        func.sum(case((unmetered, 1), else_=0)).label("unmetered_requests"),
    )


def coverage_from_values(
    cost: float | None, priced: int | None, unpriced: int | None, unmetered: int | None, *, unknown: bool = False
) -> CostCoverage:
    return CostCoverage(float(cost or 0.0), int(priced or 0), int(unpriced or 0), int(unmetered or 0), unknown)
