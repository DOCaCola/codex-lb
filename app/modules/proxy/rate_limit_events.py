"""Usage reported to clients: pool snapshots in place of the serving account's."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.config.settings_cache import get_settings_cache
from app.core.types import JsonValue
from app.core.usage.live_snapshots import LiveUsageWindow, parse_rate_limit_headers
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy.types import AdditionalRateLimitData, RateLimitWindowSnapshotData
from app.modules.usage.additional_quota_keys import normalize_quota_identifier

RATE_LIMIT_EVENT_TYPE = "codex.rate_limits"
_FAMILY_DISCRIMINATORS = ("metered_limit_name", "limit_name", "limit_id")
_DEFAULT_FAMILY = "codex"


@dataclass(frozen=True, slots=True)
class ClientUsageSnapshot:
    """One provider pool's usage, encoded as ``x-codex-*`` headers.

    ``additional`` maps normalized additional-limit identifiers to the
    ``rate_limits`` body of that family's pool event.
    """

    headers: dict[str, str]
    additional: dict[str, dict[str, JsonValue]] = field(default_factory=dict)


async def hide_upstream_quota_for_api_key_clients(api_key: ApiKeyData | None) -> bool:
    if api_key is None:
        return False
    settings = await get_settings_cache().get()
    return settings.hide_upstream_quota_from_api_keys


def project_rate_limit_event(
    payload: Mapping[str, JsonValue],
    snapshot: ClientUsageSnapshot | None,
) -> dict[str, JsonValue] | None:
    """Replace an upstream ``codex.rate_limits`` event with the pool's, never merge.

    Returns None when the pool has nothing to report for the event's family;
    the event is then withheld from the client.
    """

    if snapshot is None:
        return None
    family = _event_family(payload)
    if family == _DEFAULT_FAMILY:
        return rate_limit_event_from_headers(snapshot.headers)
    rate_limits = snapshot.additional.get(family)
    if rate_limits is None:
        return None
    event: dict[str, JsonValue] = {"type": RATE_LIMIT_EVENT_TYPE}
    for discriminator in _FAMILY_DISCRIMINATORS:
        value = payload.get(discriminator)
        if isinstance(value, str):
            event[discriminator] = value
    event["rate_limits"] = rate_limits
    return event


def rate_limit_event_from_headers(headers: Mapping[str, str]) -> dict[str, JsonValue] | None:
    snapshot = parse_rate_limit_headers(headers)
    if snapshot is None:
        return None
    event: dict[str, JsonValue] = {
        "type": RATE_LIMIT_EVENT_TYPE,
        "rate_limits": {
            "primary": _event_window(snapshot.primary),
            "secondary": _event_window(snapshot.secondary),
        },
    }
    if snapshot.credits_has is not None and snapshot.credits_unlimited is not None:
        lowered = {key.lower(): value for key, value in headers.items()}
        event["credits"] = {
            "has_credits": snapshot.credits_has,
            "unlimited": snapshot.credits_unlimited,
            "balance": lowered.get("x-codex-credits-balance"),
        }
    return event


def additional_rate_limit_events(limits: list[AdditionalRateLimitData]) -> dict[str, dict[str, JsonValue]]:
    """Index each additional family's pool ``rate_limits`` body by its identifiers."""

    indexed: dict[str, dict[str, JsonValue]] = {}
    for limit in limits:
        details = limit.rate_limit
        if details is None:
            continue
        rate_limits: dict[str, JsonValue] = {
            "primary": _snapshot_window(details.primary_window),
            "secondary": _snapshot_window(details.secondary_window),
        }
        for identifier in (limit.quota_key, limit.limit_name, limit.metered_feature):
            normalized = normalize_quota_identifier(identifier)
            if normalized is not None:
                indexed[normalized] = rate_limits
    return indexed


def _event_family(payload: Mapping[str, JsonValue]) -> str:
    for discriminator in _FAMILY_DISCRIMINATORS:
        value = payload.get(discriminator)
        if isinstance(value, str):
            return normalize_quota_identifier(value) or _DEFAULT_FAMILY
    return _DEFAULT_FAMILY


def _event_window(window: LiveUsageWindow | None) -> dict[str, JsonValue] | None:
    if window is None:
        return None
    return {
        "used_percent": window.used_percent,
        "window_minutes": window.window_minutes,
        "reset_at": window.reset_at,
    }


def _snapshot_window(window: RateLimitWindowSnapshotData | None) -> dict[str, JsonValue] | None:
    if window is None:
        return None
    return {
        "used_percent": float(window.used_percent),
        "window_minutes": window.limit_window_seconds // 60 if window.limit_window_seconds is not None else None,
        "reset_at": window.reset_at,
    }
