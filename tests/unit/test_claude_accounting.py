"""Inclusive Claude usage, semantic timing and API-equivalent price contracts."""

import json

import pytest

from app.core.usage.logs import calculated_cost_from_log, cost_breakdown_from_log
from app.core.usage.pricing import ClaudeUsageTokens, ModelPrice, calculate_claude_cost_breakdown, get_pricing_for_model
from app.db.models import ModelSource, ModelSourceModel, RequestLog
from app.modules.api_keys.service import _reserve_cost_budget_microdollars
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.native import NativeObserver
from app.modules.claude.responses import Usage
from app.modules.model_sources.catalog import source_model_cost_usd
from app.modules.model_sources.forwarding import SourceStreamUsageParser, SourceUsageHolder
from tests.simulation.virtual_time import VirtualClock

pytestmark = pytest.mark.unit


def _source() -> ModelSource:
    source = ModelSource(id="claude-account", name="Claude", kind="claude", base_url="https://invalid.test")
    source.models = [ModelSourceModel(model="anthropic/claude-haiku-4-5-20251001", is_enabled=True)]
    return source


def _frame(event: dict) -> bytes:
    return ("data: " + json.dumps(event) + "\n\n").encode()


def test_claude_cache_detail_is_inclusive_and_merges_partial_deltas():
    holder = SourceUsageHolder()
    observer = NativeObserver(holder)
    observer.consume(
        {
            "type": "message_start",
            "message": {
                "usage": {
                    "input_tokens": 100,
                    "cache_read_input_tokens": 40,
                    "cache_creation_input_tokens": 30,
                    "cache_creation": {"ephemeral_5m_input_tokens": 20, "ephemeral_1h_input_tokens": 10},
                }
            },
        }
    )
    observer.consume({"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 9}})
    assert holder.usage.input_tokens == 170
    assert holder.usage.cached_input_tokens == 40
    assert holder.usage.cache_creation_tokens == 30
    assert (holder.usage.cache_creation_5m_tokens, holder.usage.cache_creation_1h_tokens) == (20, 10)
    assert holder.usage.reasoning_tokens is None


def _native_stream(stop_reason: str, *, close_block: bool) -> NativeObserver:
    observer = NativeObserver(SourceUsageHolder())
    observer.consume({"type": "message_start", "message": {"id": "m", "usage": {"input_tokens": 1}}})
    observer.consume({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})
    if close_block:
        observer.consume({"type": "content_block_stop", "index": 0})
    observer.consume({"type": "message_delta", "delta": {"stop_reason": stop_reason}, "usage": {"output_tokens": 2}})
    return observer


@pytest.mark.parametrize(
    "stop_reason,close_block,terminal",
    [
        ("refusal", False, "incomplete"),
        ("refusal", True, "incomplete"),
        ("model_context_window_exceeded", True, "incomplete"),
        ("pause_turn", True, "incomplete"),
        ("end_turn", True, "completed"),
    ],
)
def test_native_terminal_kind(stop_reason, close_block, terminal):
    observer = _native_stream(stop_reason, close_block=close_block)
    observer.consume({"type": "message_stop"})
    assert observer.holder.terminal_kind == terminal
    assert observer.holder.successful_terminal_seen


def test_native_unfinished_non_refusal_stop_fails():
    observer = _native_stream("end_turn", close_block=False)
    with pytest.raises(ClaudeError, match=r"unfinished output \(open_blocks=1, stop_reason=end_turn\)"):
        observer.consume({"type": "message_stop"})


def test_claude_timing_ignores_metadata_and_empty_content():
    clock = VirtualClock()
    holder = SourceUsageHolder()
    parser = SourceStreamUsageParser(holder, response_shape="claude", clock=clock, started_at=clock.monotonic())
    clock.advance(1)
    parser.feed(_frame({"type": "message_start", "message": {"usage": {"input_tokens": 1}}}))
    parser.feed(_frame({"type": "ping"}))
    parser.feed(_frame({"type": "content_block_start", "content_block": {"type": "text", "text": ""}}))
    assert holder.timings.latency_first_token_ms is None
    clock.advance(2)
    parser.feed(_frame({"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "thought"}}))
    assert holder.timings.latency_first_token_ms == 3000
    clock.advance(1)
    parser.feed(_frame({"type": "message_stop"}))
    clock.advance(9)
    parser.end_timing()
    assert holder.timings.latency_ms == 4000


@pytest.mark.parametrize(
    "opaque_event",
    [
        {"type": "content_block_start", "content_block": {"type": "redacted_thinking", "data": "opaque"}},
        {"type": "content_block_start", "content_block": {"type": "thinking", "thinking": "", "signature": "signed"}},
        {"type": "content_block_delta", "delta": {"type": "signature_delta", "signature": "signed"}},
    ],
)
def test_claude_timing_observes_opaque_output_without_inventing_usage(opaque_event):
    clock = VirtualClock()
    holder = SourceUsageHolder()
    parser = SourceStreamUsageParser(holder, response_shape="claude", clock=clock)
    clock.advance(1)
    parser.feed(_frame(opaque_event))
    clock.advance(2)
    parser.feed(_frame({"type": "content_block_delta", "delta": {"type": "text_delta", "text": "answer"}}))
    clock.advance(1)
    parser.feed(_frame({"type": "message_stop"}))
    assert holder.timings.latency_first_token_ms == 1000
    assert holder.timings.latency_ms == 4000
    assert holder.usage is None


@pytest.mark.parametrize(
    "empty_event",
    [
        {"type": "content_block_start", "content_block": {"type": "redacted_thinking", "data": ""}},
        {"type": "content_block_start", "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
        {"type": "content_block_delta", "delta": {"type": "signature_delta", "signature": ""}},
        {"type": "content_block_start", "content_block": {"type": "text", "text": "", "data": "metadata"}},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
    ],
)
def test_claude_timing_ignores_empty_opaque_and_terminal_events(empty_event):
    clock = VirtualClock()
    holder = SourceUsageHolder()
    parser = SourceStreamUsageParser(holder, response_shape="claude", clock=clock)
    clock.advance(1)
    parser.feed(_frame(empty_event))
    parser.feed(_frame({"type": "message_stop"}))
    assert holder.timings.latency_first_token_ms is None
    assert holder.timings.latency_ms == 1000


def test_claude_price_counts_each_cache_category_once(monkeypatch):
    from app.core.usage import pricing_catalog

    monkeypatch.setattr(pricing_catalog, "_prices", {"claude-haiku-4-5": ModelPrice(1, 5, 0.1, 1.25, 2)})
    source = _source()
    model = source.models[0].model
    assert get_pricing_for_model(model)[0] == "claude-haiku-4-5"
    assert source_model_cost_usd(
        source,
        model,
        input_tokens=1_000_000,
        cached_input_tokens=200_000,
        cache_creation_tokens=300_000,
        cache_creation_5m_tokens=200_000,
        cache_creation_1h_tokens=100_000,
        output_tokens=100_000,
    ) == pytest.approx(0.5 + 0.02 + 0.25 + 0.2 + 0.5)
    assert (
        source_model_cost_usd(
            source,
            model,
            input_tokens=100,
            cached_input_tokens=0,
            cache_creation_tokens=10,
            output_tokens=1,
        )
        is None
    )


def test_claude_long_context_prices_all_categories_at_selected_tier():
    price = ModelPrice(
        1,
        5,
        0.1,
        1.25,
        2,
        long_context_threshold_tokens=100,
        long_context_input_per_1m=2,
        long_context_output_per_1m=10,
        long_context_cached_input_per_1m=0.2,
        long_context_cache_write_5m_per_1m=2.5,
        long_context_cache_write_1h_per_1m=4,
    )
    at_boundary = calculate_claude_cost_breakdown(ClaudeUsageTokens(100, 10, 20, 30, 20, 10), price)
    above_boundary = calculate_claude_cost_breakdown(ClaudeUsageTokens(101, 10, 20, 30, 20, 10), price)
    assert at_boundary is not None and above_boundary is not None
    assert at_boundary.total_usd == pytest.approx((50 + 2 + 25 + 20 + 50) / 1_000_000)
    assert above_boundary.total_usd == pytest.approx((102 + 4 + 50 + 40 + 100) / 1_000_000)
    missing_tier = ModelPrice(**{**price.__dict__, "long_context_cache_write_1h_per_1m": None})
    assert calculate_claude_cost_breakdown(ClaudeUsageTokens(101, 10, 20, 30, 20, 10), missing_tier) is None


def test_missing_price_is_not_free_and_explicit_zero_is_free(monkeypatch):
    from app.core.usage import pricing_catalog

    source = _source()
    model = source.models[0].model
    monkeypatch.setattr(pricing_catalog, "_prices", {})
    assert source_model_cost_usd(source, model, input_tokens=1, output_tokens=1) is None
    monkeypatch.setattr(pricing_catalog, "_prices", {"claude-haiku-4-5": ModelPrice(0, 0, 0, 0, 0)})
    assert source_model_cost_usd(source, model, input_tokens=1, output_tokens=1) == 0


def test_unreported_cache_creation_and_reasoning_stay_unknown():
    usage = Usage.model_validate({"input_tokens": 4, "output_tokens": 2})
    assert "cache_creation_tokens" not in usage.responses()["input_tokens_details"]
    assert "output_tokens_details" not in usage.responses()


def test_partial_cache_write_detail_requires_reported_total():
    with pytest.raises(ValueError, match="Claude cache creation total is missing"):
        Usage.model_validate({"cache_creation": {"ephemeral_5m_input_tokens": 10}})


def test_log_reader_never_reprices_historical_or_unknown_claude_rows(monkeypatch):
    from app.core.usage import pricing_catalog

    monkeypatch.setattr(pricing_catalog, "_prices", {"claude-haiku-4-5": ModelPrice(1, 5, 0.1, 1.25, 2)})
    log = RequestLog(
        request_id="historic",
        model="anthropic/claude-haiku-4-5-20251001",
        model_source_kind="claude",
        status="success",
        input_tokens=170,
        cached_input_tokens=40,
        output_tokens=9,
    )
    assert calculated_cost_from_log(log) is None
    assert cost_breakdown_from_log(log).total_usd is None
    log.cost_usd = 0
    assert cost_breakdown_from_log(log).total_usd is None
    log.cost_provenance = "api_equivalent_estimate"
    log.cache_creation_tokens = 30
    log.cache_creation_5m_tokens = 20
    log.cache_creation_1h_tokens = 10
    log.cost_usd = (100 + 4 + 25 + 20 + 45) / 1_000_000
    breakdown = cost_breakdown_from_log(log)
    assert breakdown.input_usd == pytest.approx(100 / 1_000_000)
    assert breakdown.cached_input_usd == pytest.approx(4 / 1_000_000)
    assert breakdown.cache_write_usd == pytest.approx(45 / 1_000_000)
    assert breakdown.output_usd == pytest.approx(45 / 1_000_000)


def test_explicitly_free_claude_log_retains_zero_price():
    log = RequestLog(
        request_id="free",
        model="anthropic/claude-haiku-4-5-20251001",
        model_source_kind="claude",
        status="success",
        cost_usd=0,
        cost_provenance="api_equivalent_estimate",
    )
    assert cost_breakdown_from_log(log).total_usd == 0


def test_other_source_using_claude_model_alias_keeps_reported_cost():
    log = RequestLog(
        request_id="openrouter",
        model="anthropic/claude-haiku-4-5-20251001",
        model_source_kind="openrouter",
        status="success",
        cost_usd=0.01,
    )
    assert cost_breakdown_from_log(log).total_usd == 0.01


def test_source_cost_never_goes_negative_when_cached_exceeds_input():
    source = ModelSource(id="compat", name="Compat", kind="openai_compatible", base_url="https://invalid.test")
    source.models = [
        ModelSourceModel(
            model="compat-model", is_enabled=True, input_per_1m=2.0, cached_input_per_1m=1.0, output_per_1m=4.0
        )
    ]
    cost = source_model_cost_usd(source, "compat-model", input_tokens=100, output_tokens=0, cached_input_tokens=300)
    assert cost == pytest.approx(300 / 1_000_000 * 1.0)


def test_cost_limit_reservation_distinguishes_explicit_free_from_missing(monkeypatch):
    from app.core.usage import pricing_catalog

    monkeypatch.setattr(pricing_catalog, "_prices", {"free": ModelPrice(0, 0)})
    assert _reserve_cost_budget_microdollars("free", None, input_tokens=100, output_tokens=10) == 0
    assert _reserve_cost_budget_microdollars("unknown", None, input_tokens=100, output_tokens=10) > 0
