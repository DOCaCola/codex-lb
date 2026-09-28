from datetime import UTC, datetime, timedelta


def overage_headers(*, now: datetime | None = None, mixed: bool = False) -> dict[str, str]:
    now = now or datetime.now(UTC)
    return {
        "anthropic-ratelimit-unified-status": "rejected",
        "anthropic-ratelimit-unified-representative-claim": "seven_day_overage_included",
        "anthropic-ratelimit-unified-5h-status": "rejected" if mixed else "allowed",
        "anthropic-ratelimit-unified-7d-status": "allowed",
        "anthropic-ratelimit-unified-7d_oi-status": "rejected",
        "anthropic-ratelimit-unified-overage-status": "rejected",
        "anthropic-ratelimit-unified-5h-reset": str((now + timedelta(hours=2)).timestamp()),
        "anthropic-ratelimit-unified-7d_oi-reset": str((now + timedelta(hours=80)).timestamp()),
        "retry-after": str(80 * 3600),
    }
