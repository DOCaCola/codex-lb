from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from app.modules.proxy._service.websocket.replay_store import HTTPFallbackReplayStore, ReplayScope


@pytest.mark.asyncio
async def test_replay_survives_restart_and_scopes_content(tmp_path):
    store = HTTPFallbackReplayStore(tmp_path)
    scope = ReplayScope("key-a", "thread-a")
    input_items = [{"role": "user", "content": "private question"}]
    output = [{"id": "fc_1", "type": "function_call", "call_id": "call_1", "arguments": "{}"}]
    delta = [{"type": "function_call_output", "call_id": "call_1", "output": "private result"}]
    await store.remember(scope, "resp_1", json.dumps({"model": "gpt-6-astra", "input": input_items}), output, "acct")
    restarted = HTTPFallbackReplayStore(tmp_path)
    retained = await restarted.load(scope, "resp_1")
    assert retained is not None
    assert retained.expand(delta) == [*input_items, *output, *delta]
    assert retained.expand([*input_items, *output, *delta]) == [*input_items, *output, *delta]
    assert retained.expand(input_items) == [*input_items, *output, *input_items]
    assert await restarted.load(ReplayScope("key-b", "thread-a"), "resp_1") is None
    assert await restarted.load(ReplayScope("key-a", "thread-b"), "resp_1") is None
    assert all(path.stat().st_mode & 0o077 == 0 for path in tmp_path.glob("*.replay"))


@pytest.mark.asyncio
async def test_replay_expires_without_extending_on_read(tmp_path):
    store = HTTPFallbackReplayStore(tmp_path, ttl_seconds=3600)
    scope = ReplayScope(None, "thread")
    await store.remember(scope, "resp", '{"model":"m","input":[]}', [], "acct")
    path = next(tmp_path.glob("*.replay"))
    stamp = path.stat().st_mtime
    assert await store.load(scope, "resp") is not None
    assert path.stat().st_mtime == stamp
    os.utime(path, (stamp - 3601, stamp - 3601))
    assert await store.load(scope, "resp") is None
    assert not path.exists()


@pytest.mark.asyncio
async def test_replay_bounds_count_disk_and_entry_size(tmp_path):
    store = HTTPFallbackReplayStore(tmp_path, max_entries=2, max_total_bytes=300, max_entry_bytes=200)
    scope = ReplayScope(None, "thread")
    for index in range(5):
        await store.remember(scope, f"resp_{index}", '{"model":"m","input":[]}', [], "acct")
    paths = list(tmp_path.glob("*.replay"))
    assert len(paths) == 2
    assert sum(path.stat().st_size for path in paths) <= 300
    assert await store.load(scope, "resp_0") is None
    assert await store.load(scope, "resp_4") is not None
    await store.remember(scope, "huge", json.dumps({"model": "m", "input": "x" * 200}), [], "acct")
    assert await store.load(scope, "huge") is None


@pytest.mark.asyncio
async def test_replay_corrupt_and_unwritable_storage_fail_closed(tmp_path):
    store = HTTPFallbackReplayStore(tmp_path)
    scope = ReplayScope(None, "thread")
    await store.remember(scope, "resp", '{"model":"m","input":[]}', [], "acct")
    path = next(tmp_path.glob("*.replay"))
    path.write_text("corrupt")
    assert await store.load(scope, "resp") is None
    invalid_store = HTTPFallbackReplayStore(path / "cannot-create-directory")
    await invalid_store.remember(scope, "resp", '{"model":"m","input":[]}', [], "acct")
    assert await invalid_store.load(scope, "resp") is None


@pytest.mark.asyncio
async def test_unresolved_delta_never_seeds_cache(tmp_path):
    store = HTTPFallbackReplayStore(tmp_path)
    scope = ReplayScope(None, "thread")
    await store.remember(scope, "resp", '{"model":"m","input":[],"previous_response_id":"missing"}', [], "acct")
    assert await store.load(scope, "resp") is None


@pytest.mark.asyncio
async def test_replay_spills_beyond_ram_budget_and_sweeps_without_requests(tmp_path):
    now = [1000.0]
    store = HTTPFallbackReplayStore(tmp_path, max_memory_bytes=200, clock=SimpleNamespace(time=lambda: now[0]))
    scope = ReplayScope(None, "thread")
    await store.remember(scope, "small", '{"model":"m","input":[]}', [], "acct")
    await store.remember(scope, "large", json.dumps({"model": "m", "input": "image" * 500}), [], "acct")
    assert sum(len(body) for _, body in store._resident.values()) <= 200
    retained = await store.load(scope, "large")
    assert retained is not None
    assert retained.input == [{"role": "user", "content": "image" * 500}]
    now[0] += 3601
    await store.sweep()
    assert not list(tmp_path.glob("*.replay"))
    assert not store._resident


@pytest.mark.asyncio
async def test_replay_concurrent_publishers_keep_disk_budget(tmp_path):
    import asyncio

    stores = [HTTPFallbackReplayStore(tmp_path, max_entries=3, max_total_bytes=500) for _ in range(2)]
    scope = ReplayScope(None, "thread")
    await asyncio.gather(
        *[
            stores[index % 2].remember(scope, f"resp_{index}", '{"model":"m","input":[]}', [], "acct")
            for index in range(10)
        ]
    )
    paths = list(tmp_path.glob("*.replay"))
    assert len(paths) == 3
    assert sum(path.stat().st_size for path in paths) <= 500
    assert not list(tmp_path.glob("*.tmp"))
