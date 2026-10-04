"""Even-consumption guidelines, distinct from provider quota observations."""

from collections.abc import Iterable, Mapping


def scheduled_remaining_percent(*, at: float, reset_at: float, window_seconds: int) -> float:
    remaining_seconds = max(0, min(window_seconds, reset_at - at))
    return round(100.0 * remaining_seconds / window_seconds, 2)


def scheduled_remaining_series(
    time_grid: Iterable[int], deadlines: Mapping[int, tuple[int, int]]
) -> list[tuple[int, float]]:
    """Plan line over a bucket grid from each bucket's latest (reset deadline, window seconds).

    A bucket without a deadline keeps the previous one; the plan starts at the first known deadline.
    """
    points: list[tuple[int, float]] = []
    current: tuple[int, int] | None = None
    for epoch in time_grid:
        current = deadlines.get(epoch, current)
        if current is not None:
            reset_at, window_seconds = current
            points.append(
                (epoch, scheduled_remaining_percent(at=epoch, reset_at=reset_at, window_seconds=window_seconds))
            )
    return points
