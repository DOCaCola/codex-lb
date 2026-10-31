from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

from app.modules.reports.filters import ReportFilters
from app.modules.reports.repository import (
    AccountIdentity,
    DailyAccountAggregateRow,
    DailyModelAggregateRow,
    DailyReportAggregateRow,
    DailyReportRangeTooLargeError,
    ReportsRepository,
    SplitMeasures,
    SummaryAggregateRow,
    UserAgentAggregateRow,
)
from app.modules.reports.service import InvalidReportDateRangeError, ReportsService

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_date", "end_date", "report_timezone"),
    [
        pytest.param(
            date(2026, 2, 15),
            date(2026, 2, 16),
            "Africa/Casablanca",
            id="casablanca-offset-to-zero",
        ),
        pytest.param(
            date(2026, 3, 22),
            date(2026, 3, 23),
            "Africa/Casablanca",
            id="casablanca-offset-from-zero",
        ),
        pytest.param(date(2026, 6, 1), date(2026, 6, 2), "UTC", id="utc"),
        pytest.param(
            date(2026, 6, 1),
            date(2026, 6, 2),
            "Africa/Casablanca",
            id="casablanca-stable-offset",
        ),
        pytest.param(
            date(2026, 6, 1),
            date(2026, 6, 2),
            "Mars/Olympus_Mons",
            id="invalid-zone-utc-fallback",
        ),
    ],
)
async def test_get_reports_averages_use_inclusive_local_calendar_days(
    start_date: date,
    end_date: date,
    report_timezone: str,
) -> None:
    summary = SummaryAggregateRow(
        total_cost_usd=60.0,
        total_input_tokens=0,
        total_output_tokens=0,
        total_reasoning_tokens=0,
        reasoning_usage_known_requests=0,
        total_cached_tokens=0,
        total_requests=30,
        conversation_count=0,
        total_errors=0,
        total_cancelled=0,
        active_accounts=1,
    )
    repo = SimpleNamespace(
        aggregate_summary=AsyncMock(side_effect=[summary, summary]),
        aggregate_daily_rows=AsyncMock(return_value=[]),
        aggregate_daily_by_model=AsyncMock(return_value=[]),
        aggregate_daily_by_account=AsyncMock(return_value=[]),
        aggregate_by_useragent=AsyncMock(return_value=[]),
        earliest_report_activity_at=AsyncMock(return_value=None),
    )
    service = ReportsService(cast(ReportsRepository, repo))

    result = await service.get_reports(
        start_date=start_date,
        end_date=end_date,
        report_timezone=report_timezone,
    )

    assert result.summary.avg_cost_per_day == 30.0
    assert result.summary.avg_requests_per_day == 15.0


@pytest.mark.asyncio
async def test_get_reports_averages_known_cost_under_incomplete_coverage() -> None:
    summary = SummaryAggregateRow(
        total_cost_usd=70.0,
        total_input_tokens=0,
        total_output_tokens=0,
        total_reasoning_tokens=0,
        reasoning_usage_known_requests=0,
        total_cached_tokens=0,
        total_requests=8,
        total_errors=0,
        active_accounts=1,
        priced_requests=7,
        unpriced_requests=1,
    )
    repo = SimpleNamespace(
        aggregate_summary=AsyncMock(side_effect=[summary, summary]),
        aggregate_daily_rows=AsyncMock(return_value=[]),
        aggregate_daily_by_model=AsyncMock(return_value=[]),
        aggregate_daily_by_account=AsyncMock(return_value=[]),
        aggregate_by_useragent=AsyncMock(return_value=[]),
        earliest_report_activity_at=AsyncMock(return_value=None),
    )
    service = ReportsService(cast(ReportsRepository, repo))

    result = await service.get_reports(start_date=date(2026, 6, 1), end_date=date(2026, 6, 7))

    assert result.summary.avg_cost_per_day == 10.0
    assert result.summary.unpriced_requests == 1


@pytest.mark.asyncio
async def test_get_reports_rejects_oversized_range_after_applying_default_end_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = SimpleNamespace(
        aggregate_summary=AsyncMock(),
        aggregate_daily_rows=AsyncMock(),
        aggregate_daily_by_model=AsyncMock(),
        aggregate_daily_by_account=AsyncMock(),
        earliest_report_activity_at=AsyncMock(),
    )
    service = ReportsService(cast(ReportsRepository, repo))
    fixed_now = datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.modules.reports.service.utcnow", lambda: fixed_now)

    with pytest.raises(DailyReportRangeTooLargeError, match="730 days or less"):
        await service.get_reports(start_date=date(2020, 1, 1))

    repo.aggregate_summary.assert_not_awaited()
    repo.aggregate_daily_rows.assert_not_awaited()
    repo.aggregate_daily_by_model.assert_not_awaited()
    repo.aggregate_daily_by_account.assert_not_awaited()
    repo.earliest_report_activity_at.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_reports_rejects_inverted_defaulted_range_before_repository_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = SimpleNamespace(
        aggregate_summary=AsyncMock(),
        aggregate_daily_rows=AsyncMock(),
        aggregate_daily_by_model=AsyncMock(),
        aggregate_daily_by_account=AsyncMock(),
        aggregate_by_useragent=AsyncMock(),
        earliest_report_activity_at=AsyncMock(),
    )
    service = ReportsService(cast(ReportsRepository, repo))
    fixed_now = datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.modules.reports.service.utcnow", lambda: fixed_now)

    with pytest.raises(
        InvalidReportDateRangeError,
        match="start_date must be on or before end_date",
    ):
        await service.get_reports(start_date=date(2026, 6, 13))

    repo.aggregate_summary.assert_not_awaited()
    repo.aggregate_daily_rows.assert_not_awaited()
    repo.aggregate_daily_by_model.assert_not_awaited()
    repo.aggregate_daily_by_account.assert_not_awaited()
    repo.aggregate_by_useragent.assert_not_awaited()
    repo.earliest_report_activity_at.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_reports_serializes_conversation_and_breakdown_request_counts() -> None:
    repo = SimpleNamespace(
        aggregate_summary=AsyncMock(
            side_effect=[
                SummaryAggregateRow(
                    total_cost_usd=1.2,
                    total_input_tokens=12,
                    total_output_tokens=6,
                    total_reasoning_tokens=4,
                    reasoning_usage_known_requests=2,
                    total_cached_tokens=2,
                    total_requests=2,
                    conversation_count=1,
                    total_errors=0,
                    total_cancelled=0,
                    active_accounts=1,
                ),
                SummaryAggregateRow(
                    total_cost_usd=0.4,
                    total_input_tokens=4,
                    total_output_tokens=2,
                    total_reasoning_tokens=2,
                    reasoning_usage_known_requests=1,
                    total_cached_tokens=0,
                    total_requests=1,
                    conversation_count=0,
                    total_errors=0,
                    total_cancelled=0,
                    active_accounts=1,
                ),
            ]
        ),
        aggregate_daily_rows=AsyncMock(
            return_value=[
                DailyReportAggregateRow(
                    date="2026-06-01",
                    requests=2,
                    conversation_count=1,
                    input_tokens=12,
                    output_tokens=6,
                    reasoning_tokens=None,
                    cached_input_tokens=2,
                    cost_usd=1.2,
                    active_accounts=1,
                    error_count=0,
                    cancelled_count=0,
                    median_ttft_ms=123.456,
                    median_tps=78.901,
                    median_queue_ms=45.678,
                )
            ]
        ),
        aggregate_daily_by_model=AsyncMock(
            return_value=[
                DailyModelAggregateRow("2026-06-01", "gpt-5.1", _measures(cost_usd=1.0, requests=1)),
                DailyModelAggregateRow("2026-06-01", "gpt-5.1-mini", _measures(cost_usd=0.2, requests=1)),
            ]
        ),
        aggregate_daily_by_account=AsyncMock(
            return_value=[
                DailyAccountAggregateRow(
                    "2026-06-01",
                    AccountIdentity("acc_reports", None, "codex", "Reports"),
                    _measures(cost_usd=1.2, requests=2),
                )
            ]
        ),
        aggregate_by_useragent=AsyncMock(
            return_value=[UserAgentAggregateRow(useragent_group="opencode", cost_usd=1.2, request_count=2)]
        ),
        earliest_report_activity_at=AsyncMock(return_value=datetime(2026, 5, 1, 0, 0, 0)),
    )
    service = ReportsService(cast(ReportsRepository, repo))
    filters = ReportFilters.create(useragent_groups=["opencode"])

    result = await service.get_reports(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 1),
        filters=filters,
    )

    repo.aggregate_summary.assert_any_await(
        datetime(2026, 6, 1, 0, 0, 0),
        datetime(2026, 6, 2, 0, 0, 0),
        filters,
    )
    for daily_method in (repo.aggregate_daily_rows, repo.aggregate_daily_by_model, repo.aggregate_daily_by_account):
        daily_method.assert_awaited_once_with(date(2026, 6, 1), date(2026, 6, 1), timezone.utc, filters)
    repo.aggregate_by_useragent.assert_awaited_once_with(
        datetime(2026, 6, 1, 0, 0, 0),
        datetime(2026, 6, 2, 0, 0, 0),
        filters,
    )
    repo.earliest_report_activity_at.assert_awaited_once_with(filters)

    assert result.daily[0].median_ttft_ms == 123.46
    assert result.daily[0].conversations == 1
    assert result.daily[0].median_tps == 78.9
    assert result.daily[0].median_queue_ms == 45.68
    assert result.daily[0].reasoning_tokens is None
    assert result.by_model[0].model == "gpt-5.1"
    assert [entry.model for entry in result.daily_by_model] == ["gpt-5.1", "gpt-5.1-mini"]
    assert result.by_account[0].cost_usd == 1.2
    assert result.daily_by_account[0].name == "Reports"
    assert result.summary.total_conversations == 1
    assert result.summary.total_reasoning_tokens == 4
    assert result.summary.reasoning_usage_known_requests == 2
    assert result.comparison.previous.total_tokens == 6
    assert [entry.requests for entry in result.by_model] == [1, 1]
    assert result.by_useragent[0].useragent == "opencode"
    assert result.by_useragent[0].requests == 2


@pytest.mark.asyncio
async def test_get_reports_sums_account_and_model_totals_from_daily_splits() -> None:
    summary = SummaryAggregateRow(
        total_cost_usd=6.0,
        total_input_tokens=0,
        total_output_tokens=0,
        total_reasoning_tokens=0,
        reasoning_usage_known_requests=0,
        total_cached_tokens=0,
        total_requests=6,
        total_errors=0,
        active_accounts=2,
    )
    codex = AccountIdentity("acc_1", None, "codex", "Codex")
    claude = AccountIdentity(None, "src_1", "claude", "Claude")
    repo = SimpleNamespace(
        aggregate_summary=AsyncMock(side_effect=[summary, summary]),
        aggregate_daily_rows=AsyncMock(return_value=[]),
        aggregate_daily_by_model=AsyncMock(
            return_value=[
                DailyModelAggregateRow("2026-06-01", "a", _measures(cost_usd=1.0, requests=1, reasoning_tokens=None)),
                DailyModelAggregateRow("2026-06-02", "a", _measures(cost_usd=2.0, requests=2, reasoning_tokens=5)),
                DailyModelAggregateRow("2026-06-02", "b", _measures(cost_usd=3.0, requests=3, unpriced_requests=1)),
            ]
        ),
        aggregate_daily_by_account=AsyncMock(
            return_value=[
                DailyAccountAggregateRow("2026-06-01", codex, _measures(cost_usd=1.0, requests=1)),
                DailyAccountAggregateRow("2026-06-02", codex, _measures(cost_usd=1.5, requests=2)),
                DailyAccountAggregateRow("2026-06-02", claude, _measures(cost_usd=3.5, requests=3)),
            ]
        ),
        aggregate_by_useragent=AsyncMock(return_value=[]),
        earliest_report_activity_at=AsyncMock(return_value=None),
    )

    result = await ReportsService(cast(ReportsRepository, repo)).get_reports(
        start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
    )

    assert [(entry.model, entry.cost_usd, entry.requests, entry.unpriced_requests) for entry in result.by_model] == [
        ("a", 3.0, 3, 0),
        ("b", 3.0, 3, 1),
    ]
    assert [(entry.model_source_id, entry.account_id, entry.cost_usd) for entry in result.by_account] == [
        ("src_1", None, 3.5),
        (None, "acc_1", 2.5),
    ]
    assert result.daily_by_model[0].reasoning_tokens is None
    assert result.daily_by_model[1].reasoning_tokens == 5


def _measures(
    *,
    cost_usd: float,
    requests: int,
    reasoning_tokens: int | None = 0,
    unpriced_requests: int = 0,
) -> SplitMeasures:
    return SplitMeasures(
        requests=requests,
        input_tokens=10 * requests,
        cached_input_tokens=5 * requests,
        output_tokens=2 * requests,
        reasoning_tokens=reasoning_tokens,
        cost_usd=cost_usd,
        error_count=0,
        priced_requests=requests - unpriced_requests,
        unpriced_requests=unpriced_requests,
    )
