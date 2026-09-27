"""Bounded provider account trend reads; no inferred quota observations."""

from datetime import UTC, datetime

from pydantic import Field
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClaudeQuotaHistory, RequestLog
from app.modules.shared.schemas import DashboardModel

HOUR = 3600
HOURS = 7 * 24


class TrendPoint(DashboardModel):
    t: datetime
    v: float | None


class TrendSeries(DashboardModel):
    key: str
    label: str
    points: list[TrendPoint] = Field(default_factory=list)


class ProviderTrends(DashboardModel):
    series: list[TrendSeries] = Field(default_factory=list)


async def read_trends(session: AsyncSession, source_id: str, *, quota: bool) -> ProviderTrends:
    end = int(datetime.now(UTC).timestamp()) // HOUR * HOUR
    start = end - (HOURS - 1) * HOUR
    since = datetime.fromtimestamp(start, UTC).replace(tzinfo=None)
    until = datetime.fromtimestamp(end + HOUR, UTC).replace(tzinfo=None)
    column = ClaudeQuotaHistory.observed_at if quota else RequestLog.requested_at
    epoch = (
        func.extract("epoch", column)
        if session.get_bind().dialect.name == "postgresql"
        else func.strftime("%s", column)
    )
    bucket = (cast(epoch, Integer) // HOUR) * HOUR
    if quota:
        rows = (
            await session.execute(
                select(ClaudeQuotaHistory.window, bucket, func.avg(ClaudeQuotaHistory.used_percent))
                .where(ClaudeQuotaHistory.source_id == source_id, column >= since, column < until)
                .group_by(ClaudeQuotaHistory.window, bucket)
            )
        ).all()
        labels = {
            "five_hour": "5-hour",
            "seven_day": "Weekly",
            "seven_day_opus": "Weekly Opus",
            "seven_day_sonnet": "Weekly Sonnet",
        }
        values: dict[str, dict[int, float]] = {}
        for window, hour, used in rows:
            values.setdefault(window, {})[hour] = max(0.0, min(100.0, 100.0 - used))
    else:
        rows = (
            await session.execute(
                select(bucket, func.count())
                .where(
                    RequestLog.model_source_id == source_id,
                    RequestLog.deleted_at.is_(None),
                    column >= since,
                    column < until,
                )
                .group_by(bucket)
            )
        ).all()
        labels = {"requests": "Requests"}
        values = {"requests": {hour: float(count) for hour, count in rows}} if rows else {}
    return ProviderTrends(
        series=[
            TrendSeries(
                key=key,
                label=label,
                points=[
                    TrendPoint(t=datetime.fromtimestamp(hour, UTC), v=values[key].get(hour, None if quota else 0.0))
                    for hour in range(start, end + HOUR, HOUR)
                ],
            )
            for key, label in labels.items()
            if key in values
        ]
    )
