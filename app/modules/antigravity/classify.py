"""Classification of Cloud Code (google.rpc) errors into account, request and capacity failures.

Structured details (ErrorInfo, RetryInfo) decide; message wording is only a fallback, following
opencodex google-errors.ts and CLIProxyAPI decideAntigravity429.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import urlparse

from app.core.types import JsonValue

FailureKind = Literal[
    "quota",
    "rate_limit",
    "unexplained_429",
    "overloaded",
    "transient",
    "auth",
    "banned",
    "verification",
    "permission",
    "location",
    "signature",
    "not_found",
    "context_length",
    "invalid_request",
    "upstream",
]

# A rate limit asking for a longer wait is quota exhaustion in effect (CLIProxyAPI).
QUOTA_RETRY_THRESHOLD = timedelta(minutes=5)
# opencodex #7803: the whole sentence, alone or with one of its two observed closing sentences.
_BAN = re.compile(
    r"^This service has been disabled in this account for violation of Terms of Service\."
    r"(?: If you believe this is an error, contact gemini-code-assist-user-feedback@google\.com\."
    r"| Please submit an appeal to continue using this product\.)?$"
)
_QUOTA_REASONS = frozenset({"QUOTA_EXHAUSTED", "INSUFFICIENT_G1_CREDITS_BALANCE"})
_QUOTA_WORDS = (
    "exhausted your capacity",
    "exhausted your quota",
    "quota exceeded",
    "exceeded your current quota",
    "quota reached",
    "weekly limit reached",
    "daily limit reached",
)
_TRANSIENT_WORDS = ("per minute", "per-minute", "requests per minute", "rate limit", "concurrent request limit")
_GO_DURATION = re.compile(r"(\d+(?:\.\d+)?)(h|ms|m|s)")


@dataclass(frozen=True)
class UpstreamFailure:
    kind: FailureKind
    status: int
    message: str
    reason: str | None = None
    retry_after: timedelta | None = None
    reset_at: datetime | None = None
    # The account-verification link; it carries a continuation token and is never logged.
    verification_url: str | None = None

    @property
    def account_scoped(self) -> bool:
        """Failures that another account may not share; request defects fail identically everywhere."""
        return self.kind in {"quota", "rate_limit", "overloaded", "transient", "auth", "banned", "verification"}


def go_duration(value: str) -> timedelta | None:
    """A Go duration ("3h12m5s", "2s", "11525.3s"); None when it is not one."""
    text = value.strip()
    if not text or _GO_DURATION.sub("", text):
        return None
    total = 0.0
    for amount, unit in _GO_DURATION.findall(text):
        total += float(amount) * {"h": 3600, "m": 60, "s": 1, "ms": 0.001}[unit]
    return timedelta(seconds=total)


def _timestamp(value: JsonValue) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def _verification_url(details: list[dict[str, JsonValue]], message: str) -> str | None:
    """Only an https://accounts.google.com link is trusted (OmniRoute antigravityVerification.ts)."""
    candidates: list[JsonValue] = []
    for detail in details:
        metadata = detail.get("metadata")
        if isinstance(metadata, dict):
            candidates += [metadata.get(key) for key in ("validation_url", "validationUrl", "appeal_url")]
        links = detail.get("links")
        for link in links if isinstance(links, list) else []:
            if isinstance(link, dict):
                candidates.append(link.get("url"))
    found = re.search(r"https://accounts\.google\.com/[^\s\"'<>]{1,2048}", message)
    if found is not None:
        candidates.append(found.group(0))
    for candidate in candidates:
        if isinstance(candidate, str):
            parsed = urlparse(candidate)
            if parsed.scheme == "https" and parsed.hostname == "accounts.google.com":
                return candidate
    return None


def classify(status: int, body: JsonValue, *, now: datetime | None = None) -> UpstreamFailure:
    now = now or datetime.now(UTC)
    error = body.get("error") if isinstance(body, dict) else None
    error = error[0] if isinstance(error, list) and error else error
    message = error.get("message") if isinstance(error, dict) else None
    message = " ".join(message.split())[:500] if isinstance(message, str) else f"HTTP {status}"
    rpc_status = error.get("status") if isinstance(error, dict) else None
    raw_details = error.get("details") if isinstance(error, dict) else None
    details = [item for item in raw_details if isinstance(item, dict)] if isinstance(raw_details, list) else []
    reason: str | None = None
    metadata: dict[str, JsonValue] = {}
    retry_after: timedelta | None = None
    for detail in details:
        kind = str(detail.get("@type", ""))
        if kind.endswith("google.rpc.ErrorInfo") and isinstance(detail.get("reason"), str):
            reason = str(detail["reason"])
            meta = detail.get("metadata")
            metadata = meta if isinstance(meta, dict) else {}
        elif kind.endswith("google.rpc.RetryInfo") and isinstance(detail.get("retryDelay"), str):
            retry_after = go_duration(str(detail["retryDelay"]))
    lower = message.lower()

    def failure(
        kind: FailureKind, *, reset_at: datetime | None = None, verification_url: str | None = None
    ) -> UpstreamFailure:
        return UpstreamFailure(kind, status, message, reason, retry_after, reset_at, verification_url)

    if status == 401 or rpc_status == "UNAUTHENTICATED":
        return failure("auth")
    if status == 403:
        if rpc_status == "PERMISSION_DENIED" and _BAN.fullmatch(message):
            return failure("banned")
        if reason == "VALIDATION_REQUIRED" or "verify your account" in lower:
            return failure("verification", verification_url=_verification_url(details, message))
        return failure("permission")
    if status == 429 or rpc_status == "RESOURCE_EXHAUSTED":
        reset_delay = metadata.get("quotaResetDelay")
        reset_at = _timestamp(metadata.get("quotaResetTimeStamp"))
        if reset_at is None and isinstance(reset_delay, str) and (delay := go_duration(reset_delay)) is not None:
            reset_at = now + delay
        quota = reason in _QUOTA_REASONS or (
            reason is None
            and any(word in lower for word in _QUOTA_WORDS)
            and not any(word in lower for word in _TRANSIENT_WORDS)
        )
        if not quota and retry_after is not None and retry_after >= QUOTA_RETRY_THRESHOLD:
            quota = True
        if quota:
            if reset_at is None and retry_after is not None:
                reset_at = now + retry_after
            return failure("quota", reset_at=reset_at)
        if reason is None and not details:
            # A bare RESOURCE_EXHAUSTED may be content-gated (CLIProxyAPI #5751, #6280); it is not quota.
            return failure("unexplained_429")
        return failure("rate_limit")
    if status == 400 or rpc_status in ("INVALID_ARGUMENT", "FAILED_PRECONDITION"):
        if "location" in lower and "not supported" in lower:
            return failure("location")
        if "signature" in lower and ("thought" in lower or "invalid" in lower):
            return failure("signature")
        if "token" in lower and ("exceeds" in lower or "too long" in lower or "context" in lower):
            return failure("context_length")
        return failure("invalid_request")
    if status == 404 or rpc_status == "NOT_FOUND":
        return failure("not_found")
    if status in (503, 529) or rpc_status == "UNAVAILABLE" or "overloaded" in lower:
        return failure("overloaded")
    if status >= 500:
        return failure("transient")
    return failure("upstream")
