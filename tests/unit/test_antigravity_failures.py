from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from app.modules.antigravity.classify import FailureKind, UpstreamFailure
from app.modules.antigravity.failures import record_failure
from app.modules.antigravity.repository import AntigravityRepository

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)


class _Repository:
    def __init__(self) -> None:
        self.cooldowns: list[tuple[str, str, datetime, str]] = []

    async def cool_down(self, source_id: str, scope: str, until: datetime, reason: str) -> None:
        self.cooldowns.append((source_id, scope, until, reason))


async def _record(kind: FailureKind, seconds: float) -> list[tuple[str, str, datetime, str]]:
    repository = _Repository()
    failure = UpstreamFailure(kind, 503, "m", retry_after=timedelta(seconds=seconds))
    await record_failure(
        cast(AntigravityRepository, cast(Any, repository)), "src-1", 1, failure, model_family="gemini-flash", now=NOW
    )
    return repository.cooldowns


@pytest.mark.parametrize(("kind", "reason"), [("overloaded", "capacity_exhausted"), ("rate_limit", "rate_limited")])
async def test_a_moving_delay_cools_the_model_on_that_account(kind: FailureKind, reason: str) -> None:
    assert await _record(kind, 17) == [("src-1", "model:gemini-flash", NOW + timedelta(seconds=17), reason)]


@pytest.mark.parametrize("kind", ["overloaded", "rate_limit"])
async def test_a_delay_waited_out_in_place_records_nothing(kind: FailureKind) -> None:
    assert await _record(kind, 2) == []
