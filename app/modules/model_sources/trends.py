"""Bounded provider account trend reads; no inferred quota observations."""

from datetime import UTC, datetime

from pydantic import Field
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage.pacing import scheduled_remaining_percent
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
    dashed: bool = False
    color_index: int = 0


class ProviderTrends(DashboardModel):
    series: list[TrendSeries] = Field(default_factory=list)


async def read_trends(session: AsyncSession, source_id: str, *, quota: bool) -> ProviderTrends:
    now = datetime.now(UTC)
    end = int(now.timestamp()) // HOUR * HOUR
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
    result = ProviderTrends(
        series=[
            TrendSeries(
                key=key,
                label=label,
                color_index=index,
                points=[
                    TrendPoint(t=datetime.fromtimestamp(hour, UTC), v=values[key].get(hour, None if quota else 0.0))
                    for hour in range(start, end + HOUR, HOUR)
                ],
            )
            for index, (key, label) in enumerate(labels.items())
            if key in values
        ]
    )
    if quota:
        observations = list(
            await session.scalars(
                select(ClaudeQuotaHistory)
                .where(
                    ClaudeQuotaHistory.source_id == source_id,
                    ClaudeQuotaHistory.window == "seven_day",
                    ClaudeQuotaHistory.observed_at >= since,
                    ClaudeQuotaHistory.observed_at <= now.replace(tzinfo=None),
                )
                .order_by(ClaudeQuotaHistory.observed_at)
            )
        )
        plan = weekly_plan(observations, start=start, end=now.timestamp())
        if plan:
            result.series.append(
                TrendSeries(key="weekly_plan", label="Weekly plan", points=plan, dashed=True, color_index=1)
            )
    return result


def weekly_plan(observations: list[ClaudeQuotaHistory], *, start: int, end: float) -> list[TrendPoint]:
    """A deadline-derived guideline; never inferred quota or an invented reset cycle."""
    events: list[tuple[float, int | None]] = []
    for observation in observations:
        at = observation.observed_at.replace(tzinfo=UTC).timestamp()
        reset = round(observation.resets_at.replace(tzinfo=UTC).timestamp()) if observation.resets_at else None
        if not events or events[-1][1] != reset:
            events.append((at, reset))
    if not any(reset is not None and reset >= at for at, reset in events):
        return []
    times = {float(hour) for hour in range(start, int(end) + 1, HOUR)} | {end}
    breaks: set[float] = set()
    for index, (at, reset) in enumerate(events):
        times.add(at)
        if index and events[index - 1][1] is not None:
            breaks.add(at - 0.001)
            times.add(at - 0.001)
        if reset is not None and at <= reset <= end:
            times.add(float(reset))
    points: list[TrendPoint] = []
    current_reset: int | None = None
    next_event = 0
    for at in sorted(times):
        while next_event < len(events) and events[next_event][0] <= at:
            current_reset = events[next_event][1]
            next_event += 1
        value = None
        if at not in breaks and current_reset is not None and at <= current_reset:
            value = scheduled_remaining_percent(at=at, reset_at=current_reset, window_seconds=HOURS * HOUR)
        points.append(TrendPoint(t=datetime.fromtimestamp(at, UTC), v=value))
    return points
