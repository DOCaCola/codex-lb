"""Capacity-pressure reclamation of idle client Responses WebSockets.

Codex keeps one Responses WebSocket per thread across turns and chains each
request onto the previous response on that socket, so a quiet socket is a
client between turns or running tools, not an abandoned one. Sockets are
therefore never closed on a timer; only when the WebSocket admission lane is
full is the least recently used idle socket asked to close, making room for
the new handshake (opencodex reclaims the same way).
"""

from __future__ import annotations

from typing import Protocol

# How long a full-lane handshake waits for the reclaimed socket's slot. The
# socket closes from its own receive loop, which wakes at least once a second.
WEBSOCKET_RECLAIM_ADMISSION_WAIT_SECONDS = 5.0


class ReclaimableWebSocket(Protocol):
    @property
    def last_activity_at(self) -> float: ...

    def reclaimable(self) -> bool: ...

    def request_reclaim(self) -> None: ...


class IdleWebSocketReclaimer:
    def __init__(self) -> None:
        self._sockets: set[ReclaimableWebSocket] = set()

    def register(self, socket: ReclaimableWebSocket) -> None:
        self._sockets.add(socket)

    def unregister(self, socket: ReclaimableWebSocket) -> None:
        self._sockets.discard(socket)

    def reclaim_least_recently_used(self) -> bool:
        """Ask the least recently used idle socket to close; False when none is idle."""
        victim = min(
            (socket for socket in self._sockets if socket.reclaimable()),
            key=lambda socket: socket.last_activity_at,
            default=None,
        )
        if victim is None:
            return False
        victim.request_reclaim()
        return True


_reclaimer = IdleWebSocketReclaimer()


def get_idle_websocket_reclaimer() -> IdleWebSocketReclaimer:
    return _reclaimer


__all__ = [
    "WEBSOCKET_RECLAIM_ADMISSION_WAIT_SECONDS",
    "IdleWebSocketReclaimer",
    "ReclaimableWebSocket",
    "get_idle_websocket_reclaimer",
]
