from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.antigravity.quota import current_buckets, family_quota, parse_summary, plan_type, window_status
from app.modules.antigravity.schemas import AccountState, QuotaBucket, Subscription, Tier

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def _bucket(bucket_id: str, fraction: float, reset: str | None = None, **extra: object) -> dict[str, Any]:
    return {"bucketId": bucket_id, "remainingFraction": fraction, "resetTime": reset, **extra}


def test_summary_maps_groups_and_windows_to_families() -> None:
    buckets = parse_summary(
        {
            "quotaSummary": {
                "groups": [
                    {
                        "groupId": "gemini",
                        "buckets": [
                            _bucket("gemini-5h", 0.5, "2026-10-29T15:00:00Z"),
                            _bucket("gemini-weekly", 0.9),
                            _bucket("gemini-argon-weekly", 0.2),
                            _bucket("gemini-daily", 0.1),
                            _bucket("gemini-session", 0.0, disabled=True),
                        ],
                    },
                    {
                        "displayName": "Claude & GPT",
                        "buckets": [{"window": "7d", "remaining": {"remainingFraction": 1.4}}],
                    },
                ]
            }
        }
    )
    readings = {(bucket.family, bucket.window): bucket for bucket in buckets}
    assert set(readings) == {("gemini", "five_hour"), ("gemini", "weekly"), ("argon", "weekly"), ("claude", "weekly")}
    assert readings[("gemini", "five_hour")].resets_at == datetime(2026, 10, 29, 15, tzinfo=UTC)
    assert readings[("claude", "weekly")].remaining_fraction == 1.0


def test_plan_types() -> None:
    def subscription(paid: str | None, current: str = "standard-tier") -> Subscription:
        return Subscription(current_tier=Tier(id=current), paid_tier=Tier(id=paid) if paid else None, observed_at=NOW)

    assert plan_type(None) == "unknown"
    assert plan_type(subscription(None)) == "free"
    # Google reports the free tier as the paid tier too ("Antigravity Starter Quota").
    assert plan_type(subscription("free-tier", "free-tier")) == "free"
    assert plan_type(subscription(None, "enterprise-tier")) == "unknown"
    assert plan_type(subscription("g1-pro-tier")) == "pro"
    assert plan_type(subscription("g1-ultra-lite-tier")) == "ultra_5x"
    assert plan_type(subscription("g1-ultra-tier")) == "ultra_20x"


def _state(*buckets: QuotaBucket) -> AccountState:
    return AccountState(quota=list(buckets))


def test_passed_resets_are_never_exhaustion_evidence() -> None:
    stale = QuotaBucket(family="gemini", window="five_hour", remaining_fraction=0, resets_at=NOW - timedelta(minutes=1))
    assert current_buckets(_state(stale), NOW) == []
    assert not family_quota(_state(stale), "gemini", NOW).blocked


def test_family_is_blocked_by_either_window() -> None:
    five = QuotaBucket(family="gemini", window="five_hour", remaining_fraction=0, resets_at=NOW + timedelta(hours=2))
    weekly = QuotaBucket(family="gemini", window="weekly", remaining_fraction=0.6, resets_at=NOW + timedelta(days=3))
    quota = family_quota(_state(five, weekly), "gemini", NOW)
    assert quota.blocked
    assert quota.retry_at == five.resets_at
    assert quota.binding == five
    assert not family_quota(_state(five, weekly), "claude", NOW).blocked


def test_window_status_reports_used_percent() -> None:
    weekly = QuotaBucket(family="argon", window="weekly", remaining_fraction=0.25)
    [status] = window_status(_state(weekly), NOW)
    assert (status.family, status.window, status.used_percent, status.exhausted) == ("argon", "weekly", 75.0, False)
