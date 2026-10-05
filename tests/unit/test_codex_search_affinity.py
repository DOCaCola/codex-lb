from __future__ import annotations

import json

from app.db.models import StickySessionKind
from app.modules.proxy.affinity import (
    _codex_search_identity,
    _codex_session_selection_key,
    _sticky_key_for_codex_search_request,
    _thread_codex_session_affinity,
)


def _metadata_headers(**metadata: str) -> dict[str, str]:
    return {"x-codex-turn-metadata": json.dumps(metadata)}


def test_search_identity_prefers_turn_metadata_over_body_id() -> None:
    identity = _codex_search_identity(
        {"id": "body-session"},
        _metadata_headers(session_id="metadata-session", thread_id="thread-1", turn_id="turn-1"),
    )

    assert identity.process_session == "metadata-session"
    assert identity.thread_id == "thread-1"


def test_search_identity_uses_body_id_without_metadata() -> None:
    identity = _codex_search_identity({"id": "body-session"}, {})

    assert identity.process_session == "body-session"
    assert identity.thread_id is None


def test_search_identity_ignores_unparseable_metadata() -> None:
    identity = _codex_search_identity({"id": "body-session"}, {"x-codex-turn-metadata": "not-json"})

    assert identity.process_session == "body-session"
    assert identity.thread_id is None


def test_search_thread_affinity_matches_the_conversation_turn_key() -> None:
    identity = _codex_search_identity(
        {"id": "process-shared"},
        _metadata_headers(session_id="process-shared", thread_id="thread-child"),
    )

    policy = _sticky_key_for_codex_search_request(identity, codex_session_affinity=True, max_age_seconds=3600)
    turn_policy = _thread_codex_session_affinity(
        {"session-id": "process-shared", "thread-id": "thread-child"},
        enabled=True,
        max_age_seconds=3600,
    )

    assert turn_policy is not None
    assert policy == turn_policy
    assert policy.kind == StickySessionKind.PROMPT_CACHE


def test_search_without_thread_uses_process_session_affinity() -> None:
    policy = _sticky_key_for_codex_search_request(
        _codex_search_identity({"id": "process-only"}, {}),
        codex_session_affinity=True,
        max_age_seconds=3600,
    )

    assert policy.kind == StickySessionKind.CODEX_SESSION
    assert policy.selection_key == _codex_session_selection_key("process-only")
    assert policy.legacy_selection_key == "process-only"


def test_search_affinity_disabled_has_no_sticky_key() -> None:
    policy = _sticky_key_for_codex_search_request(
        _codex_search_identity({"id": "process-only"}, _metadata_headers(thread_id="thread-1")),
        codex_session_affinity=False,
        max_age_seconds=3600,
    )

    assert policy.key is None
