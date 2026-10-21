from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from app.modules.request_logs.trace import CacheEvent, TraceSample, cache_event, idle_gap, prompt_split

pytestmark = pytest.mark.unit

BASE = datetime(2026, 10, 22, 12, 0, 0)


def sample(*, after_s: float = 60, prompt: int = 100_000, reads: int = 0) -> TraceSample:
    return TraceSample(
        requested_at=BASE + timedelta(seconds=after_s),
        latency_ms=1000,
        model="gpt-6.1-sol",
        provider_account=("acc-a", None),
        request_operation="responses",
        prompt_tokens=prompt,
        cache_read_tokens=reads,
        cache_write_1h_tokens=0,
    )


PREVIOUS = sample(after_s=0, prompt=100_000, reads=95_000)


def test_prompt_split_clamps_reads_to_the_prompt():
    assert prompt_split(None, None) == (0, 0)
    assert prompt_split(1000, 1500) == (1000, 1000)
    assert prompt_split(1000, -5) == (1000, 0)


def test_idle_gap_runs_from_the_previous_end():
    assert idle_gap(sample(after_s=61), PREVIOUS) == timedelta(seconds=60)
    assert idle_gap(sample(after_s=0.5), PREVIOUS) == timedelta(0)


@pytest.mark.parametrize(
    "current,previous,expected",
    [
        (sample(prompt=120_000, reads=100_000), PREVIOUS, None),
        (sample(prompt=30_000), None, CacheEvent.FIRST),
        (replace(sample(), request_operation="compaction"), PREVIOUS, CacheEvent.COMPACTION),
        (sample(), replace(PREVIOUS, request_operation="compaction"), CacheEvent.COMPACTION),
        (replace(sample(), model="claude-opus-5-5"), PREVIOUS, CacheEvent.MODEL_SWITCH),
        (replace(sample(), provider_account=("acc-b", None)), PREVIOUS, CacheEvent.ACCOUNT_SWITCH),
        (replace(sample(), provider_account=(None, "source-claude")), PREVIOUS, CacheEvent.ACCOUNT_SWITCH),
        (sample(after_s=302), PREVIOUS, CacheEvent.IDLE_EXPIRY),
        (replace(sample(after_s=1800), cache_write_1h_tokens=90_000), PREVIOUS, CacheEvent.BUST),
        (replace(sample(after_s=3700), cache_write_1h_tokens=90_000), PREVIOUS, CacheEvent.IDLE_EXPIRY),
        (sample(prompt=101_000, reads=5_000), PREVIOUS, CacheEvent.BUST),
        (sample(prompt=150_000, reads=95_000), PREVIOUS, CacheEvent.GROWTH),
        (sample(prompt=100_000, reads=40_000), PREVIOUS, CacheEvent.MISS),
    ],
)
def test_cache_event_explains_large_misses(current, previous, expected):
    assert cache_event(current, previous) == expected
