"""Per-request cache trace of one conversation.

Cache events follow Agent LB's session trace (``cache_kind``), adapted to rows of
both providers: Codex rows report no cache writes, so a miss is the uncached part of
the prompt rather than the written part. Claude rows count writes as uncached.

Idle expiry is only inferred where the cache lifetime is known. Claude documents a
5-minute and a 1-hour tier and reports which one was written. Signed-in Codex
accounts keep their cache indefinitely (OpenAI, 2026-10-20), so idle time never
explains a Codex miss; other model sources do not report a lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.core.usage.request_operation import RequestOperation
from app.modules.claude.schemas import CLAUDE_KIND

# A miss smaller than this is ordinary growth of the prompt (Agent LB's threshold).
MISS_THRESHOLD_TOKENS = 20_000
# Claude prompt-cache lifetimes: 5 minutes by default, 1 hour when the miss was
# rewritten into the 1-hour tier (Agent LB compares the 1-hour share the same way).
CLAUDE_CACHE_TTL = timedelta(minutes=5)
CLAUDE_EXTENDED_CACHE_TTL = timedelta(hours=1)


class CacheEvent(StrEnum):
    FIRST = "first"
    COMPACTION = "compaction"
    MODEL_SWITCH = "model_switch"
    ACCOUNT_SWITCH = "account_switch"
    IDLE_EXPIRY = "idle_expiry"
    BUST = "bust"
    GROWTH = "growth"
    MISS = "miss"


@dataclass(frozen=True, slots=True)
class TraceSample:
    """The fields of one request that decide its cache behaviour."""

    requested_at: datetime
    latency_ms: int | None
    model: str
    provider_account: tuple[str | None, str | None]
    request_operation: str | None
    prompt_tokens: int
    cache_read_tokens: int
    cache_lifetime: timedelta | None


def cache_lifetime(model_source_kind: str | None, cache_write_1h_tokens: int | None) -> timedelta | None:
    """The prompt-cache lifetime of a request's provider, or ``None`` when idle time cannot expire it."""
    if model_source_kind != CLAUDE_KIND:
        return None
    return CLAUDE_EXTENDED_CACHE_TTL if cache_write_1h_tokens else CLAUDE_CACHE_TTL


def prompt_split(input_tokens: int | None, cached_input_tokens: int | None) -> tuple[int, int]:
    """Return the inclusive prompt size and its cache reads, clamped like conversation totals."""
    prompt = max(input_tokens or 0, 0)
    return prompt, max(0, min(cached_input_tokens or 0, prompt))


def idle_gap(sample: TraceSample, previous: TraceSample) -> timedelta:
    """Time between the previous request's end and this request's start."""
    previous_end = previous.requested_at + timedelta(milliseconds=previous.latency_ms or 0)
    return max(sample.requested_at - previous_end, timedelta(0))


def cache_event(sample: TraceSample, previous: TraceSample | None) -> CacheEvent | None:
    """Explain a large uncached prompt by its most likely cause."""
    uncached = sample.prompt_tokens - sample.cache_read_tokens
    if uncached <= MISS_THRESHOLD_TOKENS:
        return None
    if previous is None:
        return CacheEvent.FIRST
    if RequestOperation.COMPACTION in (sample.request_operation, previous.request_operation):
        return CacheEvent.COMPACTION
    if sample.model != previous.model:
        return CacheEvent.MODEL_SWITCH
    if sample.provider_account != previous.provider_account:
        return CacheEvent.ACCOUNT_SWITCH
    if sample.cache_lifetime is not None and idle_gap(sample, previous) > sample.cache_lifetime:
        return CacheEvent.IDLE_EXPIRY
    prior = previous.prompt_tokens
    reads = sample.cache_read_tokens
    if reads < prior * 0.1 and 0.95 * prior <= sample.prompt_tokens <= 1.2 * prior:
        return CacheEvent.BUST
    if reads >= prior * 0.9:
        return CacheEvent.GROWTH
    return CacheEvent.MISS
