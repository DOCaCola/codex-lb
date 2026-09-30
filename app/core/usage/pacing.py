"""Even-consumption guidelines, distinct from provider quota observations."""


def scheduled_remaining_percent(*, at: float, reset_at: float, window_seconds: int) -> float:
    remaining_seconds = max(0, min(window_seconds, reset_at - at))
    return round(100.0 * remaining_seconds / window_seconds, 2)
