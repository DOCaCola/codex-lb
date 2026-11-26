from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.modules.antigravity.classify import classify, go_duration

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
BAN = "This service has been disabled in this account for violation of Terms of Service."


def _error(status: str, message: str, *details: dict[str, Any]) -> dict[str, Any]:
    return {"error": {"code": 0, "status": status, "message": message, "details": list(details)}}


def _info(reason: str, **metadata: str) -> dict[str, Any]:
    return {"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason, "metadata": metadata}


def _retry(delay: str) -> dict[str, Any]:
    return {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": delay}


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("2s", 2), ("3h12m5s", 3 * 3600 + 12 * 60 + 5), ("11525.3s", 11525.3), ("250ms", 0.25)],
)
def test_go_duration(text: str, seconds: float) -> None:
    assert go_duration(text) == timedelta(seconds=seconds)


@pytest.mark.parametrize("text", ["", "soon", "5 minutes", "2s later"])
def test_go_duration_rejects_other_text(text: str) -> None:
    assert go_duration(text) is None


def test_structured_quota_reason_wins_over_wording() -> None:
    failure = classify(
        429,
        _error(
            "RESOURCE_EXHAUSTED",
            "Too many requests per minute",
            _info("QUOTA_EXHAUSTED", quotaResetTimeStamp="2026-10-29T15:00:00Z"),
        ),
        now=NOW,
    )
    assert failure.kind == "quota"
    assert failure.reset_at == datetime(2026, 10, 29, 15, tzinfo=UTC)
    assert failure.account_scoped


def test_quota_reset_delay_is_relative_to_now() -> None:
    failure = classify(
        429, _error("RESOURCE_EXHAUSTED", "x", _info("QUOTA_EXHAUSTED", quotaResetDelay="1h30m")), now=NOW
    )
    assert failure.reset_at == NOW + timedelta(hours=1, minutes=30)


def test_long_retry_delay_is_quota_in_effect() -> None:
    failure = classify(
        429, _error("RESOURCE_EXHAUSTED", "slow down", _info("RATE_LIMIT_EXCEEDED"), _retry("600s")), now=NOW
    )
    assert failure.kind == "quota"
    assert failure.reset_at == NOW + timedelta(minutes=10)


def test_short_rate_limit_keeps_its_retry_delay() -> None:
    failure = classify(
        429, _error("RESOURCE_EXHAUSTED", "slow down", _info("RATE_LIMIT_EXCEEDED"), _retry("1.5s")), now=NOW
    )
    assert failure.kind == "rate_limit"
    assert failure.retry_after == timedelta(seconds=1.5)


def test_quota_wording_needs_no_transient_hint() -> None:
    assert classify(429, _error("RESOURCE_EXHAUSTED", "You have exhausted your capacity"), now=NOW).kind == "quota"
    assert (
        classify(429, _error("RESOURCE_EXHAUSTED", "Quota exceeded for requests per minute"), now=NOW).kind
        == "rate_limit"
    )


def test_bare_resource_exhausted_is_not_quota() -> None:
    assert classify(429, _error("RESOURCE_EXHAUSTED", "Resource has been exhausted"), now=NOW).kind == "unexplained_429"


@pytest.mark.parametrize(
    ("header", "kind", "delay"),
    [("2", "rate_limit", timedelta(seconds=2)), ("0", "rate_limit", timedelta(0)), ("600", "quota", None)],
)
def test_retry_after_header_is_the_fallback_delay(header: str, kind: str, delay: timedelta | None) -> None:
    failure = classify(
        429, _error("RESOURCE_EXHAUSTED", "slow down", _info("RATE_LIMIT_EXCEEDED")), retry_after_header=header, now=NOW
    )
    assert failure.kind == kind
    if delay is not None:
        assert failure.retry_after == delay
    else:
        assert failure.reset_at == NOW + timedelta(minutes=10)


def test_retry_info_wins_over_the_retry_after_header() -> None:
    failure = classify(
        429,
        _error("RESOURCE_EXHAUSTED", "slow down", _info("RATE_LIMIT_EXCEEDED"), _retry("1.5s")),
        retry_after_header="600",
        now=NOW,
    )
    assert (failure.kind, failure.retry_after) == ("rate_limit", timedelta(seconds=1.5))


def test_retry_after_http_date_is_relative_to_now() -> None:
    failure = classify(
        429,
        _error("RESOURCE_EXHAUSTED", "slow down", _info("RATE_LIMIT_EXCEEDED")),
        retry_after_header="Thu, 29 Oct 2026 12:00:02 GMT",
        now=NOW,
    )
    assert failure.retry_after == timedelta(seconds=2)


def test_bare_resource_exhausted_keeps_a_long_header_delay_without_becoming_quota() -> None:
    failure = classify(
        429, _error("RESOURCE_EXHAUSTED", "Resource has been exhausted"), retry_after_header="600", now=NOW
    )
    assert (failure.kind, failure.retry_after) == ("unexplained_429", timedelta(minutes=10))


def test_capacity_errors_carry_their_retry_delay() -> None:
    capacity = _error("UNAVAILABLE", "No capacity available for model", _info("MODEL_CAPACITY_EXHAUSTED"))
    assert classify(503, capacity, retry_after_header="17", now=NOW).retry_after == timedelta(seconds=17)
    capacity["error"]["details"].append(_retry("17s"))
    failure = classify(503, capacity, retry_after_header="90", now=NOW)
    assert (failure.kind, failure.retry_after) == ("overloaded", timedelta(seconds=17))


def test_retry_after_header_is_ignored_on_request_defects() -> None:
    assert classify(400, _error("INVALID_ARGUMENT", "bad"), retry_after_header="5", now=NOW).retry_after is None


@pytest.mark.parametrize("message", ["Too many requests, slow down", "Please try again later"])
def test_bare_429_with_retry_wording_is_a_rate_limit(message: str) -> None:
    assert classify(429, _error("RESOURCE_EXHAUSTED", message), now=NOW).kind == "rate_limit"


def test_ban_requires_the_exact_sentence() -> None:
    assert classify(403, _error("PERMISSION_DENIED", BAN)).kind == "banned"
    assert (
        classify(
            403, _error("PERMISSION_DENIED", BAN + " Please submit an appeal to continue using this product.")
        ).kind
        == "banned"
    )
    assert classify(403, _error("PERMISSION_DENIED", "Quoted: " + BAN)).kind == "permission"


def test_structured_tos_violation_is_a_ban_whatever_the_wording_or_status() -> None:
    tos = _info("TOS_VIOLATION", appeal_url="https://forms.gle/x", appeal_url_link_text="Submit Appeal")
    assert classify(403, _error("PERMISSION_DENIED", "Service disabled.", tos)).kind == "banned"
    # An error frame inside an HTTP 200 stream carries the status in its body code.
    assert classify(200, _error("PERMISSION_DENIED", "Service disabled.", tos)).kind == "banned"
    assert classify(403, _error("PERMISSION_DENIED", "Service disabled.", _info("OTHER"))).kind == "permission"


def test_verification_trusts_only_google_account_links() -> None:
    trusted = classify(
        403,
        _error(
            "PERMISSION_DENIED",
            "Please verify your account",
            _info("VALIDATION_REQUIRED", validation_url="https://accounts.google.com/signin/continue?x=1"),
        ),
    )
    assert trusted.kind == "verification"
    assert trusted.verification_url == "https://accounts.google.com/signin/continue?x=1"
    spoofed = classify(
        403,
        _error("PERMISSION_DENIED", "verify", _info("VALIDATION_REQUIRED", validation_url="https://evil.example/x")),
    )
    assert spoofed.kind == "verification"
    assert spoofed.verification_url is None


@pytest.mark.parametrize(
    ("status", "rpc", "message", "kind"),
    [
        (401, "UNAUTHENTICATED", "Request had invalid authentication credentials.", "auth"),
        (400, "FAILED_PRECONDITION", "User location is not supported for the API use.", "location"),
        (400, "INVALID_ARGUMENT", "Invalid thought signature in function call.", "signature"),
        (400, "INVALID_ARGUMENT", "The input token count exceeds the maximum.", "context_length"),
        (400, "INVALID_ARGUMENT", "Unknown field.", "invalid_request"),
        (404, "NOT_FOUND", "Model not found.", "not_found"),
        (503, "UNAVAILABLE", "The model is overloaded.", "overloaded"),
        (500, "INTERNAL", "Internal error.", "transient"),
    ],
)
def test_status_classification(status: int, rpc: str, message: str, kind: str) -> None:
    assert classify(status, _error(rpc, message)).kind == kind


def test_request_defects_are_not_account_scoped() -> None:
    assert not classify(400, _error("INVALID_ARGUMENT", "Unknown field.")).account_scoped
    assert not classify(403, _error("PERMISSION_DENIED", "no")).account_scoped


def test_non_json_body_uses_status() -> None:
    failure = classify(502, "bad gateway")
    assert failure.kind == "transient"
    assert failure.message == "HTTP 502"
