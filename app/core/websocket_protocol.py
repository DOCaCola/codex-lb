"""Uvicorn WebSocket protocol whose keepalive treats inbound data as liveness.

Uvicorn's sans-I/O WebSocket protocol pings the client every
``ws_ping_interval`` seconds and fails the connection with 1011 when the
matching pong is not back within ``ws_ping_timeout`` seconds, even while the
client is still streaming frame bytes to us. Clients that write and read in a
single loop (the Codex Responses websocket pump) cannot answer a ping until
their current message is fully written, so a large ``response.create``
uploaded over a slow link (a full-history resend of ~100 MB at ~2 MB/s) was
cut off after exactly ``ping_interval + ping_timeout`` seconds, on every
reconnect attempt.

A peer that is delivering bytes is demonstrably alive. Here, receiving any
data while a ping is outstanding satisfies that ping: the pong deadline is
cancelled and the next ping is scheduled. A peer that sends nothing at all is
still closed after ``ws_ping_timeout``. This matches how codex-lb judges the
upstream side (``app.core.clients.codex.UpstreamWebSocketLiveness``).
"""

from __future__ import annotations

from uvicorn.protocols.websockets.websockets_sansio_impl import WebSocketsSansIOProtocol


class InboundLivenessWebSocketProtocol(WebSocketsSansIOProtocol):
    def data_received(self, data: bytes) -> None:
        super().data_received(data)
        if self.pong_timer is None:
            return
        self.pong_timer.cancel()
        self.pong_timer = None
        self.pending_ping_payload = None
        self.schedule_ping()
