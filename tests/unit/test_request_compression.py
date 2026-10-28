from __future__ import annotations

import logging
import threading

import pytest
import zstandard

from app.core.clients import request_compression

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("body", ["{}", '{ "text": "café", "image": "' + "A" * (2 * 1024 * 1024) + '" }'])
async def test_compressed_json_preserves_exact_bytes_and_headers(body, monkeypatch, caplog):
    event_loop_thread = threading.get_ident()
    compress = request_compression._compress_json
    calls = []

    def in_worker(text):
        calls.append(threading.get_ident())
        return compress(text)

    monkeypatch.setattr(request_compression, "_compress_json", in_worker)
    headers = {"authorization": "Bearer test", "content-type": "text/plain", "CONTENT-LENGTH": "999"}
    with caplog.at_level(logging.DEBUG, logger=request_compression.__name__):
        encoded, prepared = await request_compression.prepare_compressed_json(body, headers)

    assert len(calls) == 1
    assert calls[0] != event_loop_thread
    assert encoded == zstandard.ZstdCompressor(level=3).compress(body.encode("utf-8"))
    assert zstandard.ZstdDecompressor().decompress(encoded) == body.encode("utf-8")
    assert prepared == {
        "authorization": "Bearer test",
        "content-type": "application/json",
        "CONTENT-LENGTH": str(len(encoded)),
        "Content-Encoding": "zstd",
    }
    assert list(prepared)[:3] == list(headers)
    assert headers["CONTENT-LENGTH"] == "999"
    records = [record for record in caplog.records if record.name == request_compression.__name__]
    assert len(records) == 1
    assert f"pre_compression_bytes={len(body.encode('utf-8'))}" in records[0].message
    assert f"post_compression_bytes={len(encoded)}" in records[0].message
    assert "compression_duration_ms=" in records[0].message


@pytest.mark.asyncio
@pytest.mark.parametrize("header", ["Content-Encoding", "content-encoding", "CONTENT-ENCODING"])
async def test_compressed_json_rejects_existing_encoding(header):
    with pytest.raises(ValueError, match="content-encoding is already set"):
        await request_compression.prepare_compressed_json("{}", {header: "zstd"})


@pytest.mark.asyncio
async def test_compression_error_is_not_retried(monkeypatch):
    calls = []

    def fail(body):
        calls.append(body)
        raise zstandard.ZstdError("compression failed")

    monkeypatch.setattr(request_compression, "_compress_json", fail)
    with pytest.raises(zstandard.ZstdError, match="compression failed"):
        await request_compression.prepare_compressed_json("{}", {})
    assert calls == ["{}"]
