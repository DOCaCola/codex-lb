"""Account and additional-quota routing policy normalization."""

from __future__ import annotations

import json

from app.core.balancer import ROUTING_POLICY_BURN_FIRST, ROUTING_POLICY_PRESERVE
from app.modules.usage.additional_quota_keys import (
    canonicalize_additional_quota_key,
    get_additional_quota_routing_policy,
    normalize_additional_quota_key,
)

_ROUTING_POLICY_NORMAL = "normal"
_ACCOUNT_ROUTING_POLICIES = frozenset({_ROUTING_POLICY_NORMAL, ROUTING_POLICY_BURN_FIRST, ROUTING_POLICY_PRESERVE})
_ADDITIONAL_QUOTA_ROUTING_POLICIES = _ACCOUNT_ROUTING_POLICIES | frozenset({"inherit"})


def _normalize_account_routing_policy(value: str | None) -> str:
    if value in _ACCOUNT_ROUTING_POLICIES:
        return value
    return _ROUTING_POLICY_NORMAL


def _additional_quota_routing_policy_override(limit_name: str | None, policies: dict[str, str]) -> str | None:
    if limit_name is None:
        return None
    normalized_limit_name = canonicalize_additional_quota_key(limit_name=limit_name)
    if normalized_limit_name is None:
        return None
    policy = get_additional_quota_routing_policy(normalized_limit_name, overrides=policies)
    if policy == "inherit":
        return None
    return policy


def _parse_additional_quota_routing_policies(raw_policies: str) -> dict[str, str]:
    if not raw_policies:
        return {}
    try:
        parsed = json.loads(raw_policies)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    policies: dict[str, str] = {}
    for quota_key, policy in parsed.items():
        if not isinstance(quota_key, str) or not isinstance(policy, str):
            continue
        normalized_key = normalize_additional_quota_key(quota_key)
        normalized_policy = policy.strip().lower()
        if normalized_key and normalized_policy in _ADDITIONAL_QUOTA_ROUTING_POLICIES:
            policies[normalized_key] = normalized_policy
    return policies
