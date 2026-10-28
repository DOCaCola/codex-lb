"""Wire encoding for native ChatGPT HTTP Responses requests."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Mapping

import zstandard

logger = logging.getLogger(__name__)


def _compress_json(body: str) -> bytes:
    raw = body.encode("utf-8")
    started_at = time.monotonic()
    compressed = zstandard.ZstdCompressor(level=3).compress(raw)
    logger.debug(
        "Compressed request body with zstd pre_compression_bytes=%d post_compression_bytes=%d "
        "compression_duration_ms=%.3f",
        len(raw),
        len(compressed),
        (time.monotonic() - started_at) * 1000,
    )
    return compressed


async def prepare_compressed_json(body: str, headers: Mapping[str, str]) -> tuple[bytes, dict[str, str]]:
    """Prepare bytes once for all HTTP egress attempts, keeping CPU work off the loop."""
    if any(name.lower() == "content-encoding" for name in headers):
        raise ValueError("request compression was requested but content-encoding is already set")
    compressed = await asyncio.to_thread(_compress_json, body)
    content_headers = {"content-type": "application/json", "content-length": str(len(compressed))}
    prepared_headers = {name: content_headers.get(name.lower(), value) for name, value in headers.items()}
    missing = content_headers.keys() - {name.lower() for name in headers}
    for name in content_headers:
        if name in missing:
            prepared_headers[name.title()] = content_headers[name]
    prepared_headers["Content-Encoding"] = "zstd"
    return compressed, prepared_headers
