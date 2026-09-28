from datetime import timedelta

import pytest

from app.core.utils.time import utcnow
from app.db.models import ClaudeSessionOwner
from app.db.session import SessionLocal
from app.modules.claude.resources import resource_ids
from app.modules.claude.session import NATIVE_SESSION_TTL, NativeSessionOwnership
from tests.integration import test_claude_routing as fixtures

pool = fixtures.pool
pytestmark = pytest.mark.integration


def owner(session, *, client="client", conversation="thread", model=fixtures.MODEL):
    return NativeSessionOwnership(session, client_scope=client, conversation_id=conversation, model=model)


async def test_native_owner_survives_new_session_and_cannot_be_replaced(pool):
    async with SessionLocal() as session:
        assert await owner(session).claim(pool[0]) == pool[0]
    async with SessionLocal() as session:
        retained = owner(session)
        assert await retained.owner() == pool[0]
        assert await retained.claim(pool[1]) == pool[0]
        row = await session.get(ClaudeSessionOwner, retained.key)
        assert row is not None
        assert utcnow() < row.expires_at <= utcnow() + NATIVE_SESSION_TTL
    async with SessionLocal() as session:
        assert await owner(session, client="another").owner() is None
        assert await owner(session, conversation="another").owner() is None
        assert await owner(session, model="anthropic/claude-sonnet-5").owner() is None


async def test_expired_affinity_allows_new_account(pool):
    async with SessionLocal() as session:
        retained = owner(session)
        await retained.claim(pool[0])
        row = await session.get(ClaudeSessionOwner, retained.key)
        assert row is not None
        row.expires_at = utcnow() - timedelta(seconds=1)
        await session.commit()
    async with SessionLocal() as session:
        retained = owner(session)
        assert await retained.owner() is None
        assert await retained.claim(pool[1]) == pool[1]


async def test_soft_rebind_uses_compare_and_swap(pool):
    async with SessionLocal() as session:
        retained = owner(session)
        await retained.claim(pool[0])
        assert await retained.claim(pool[1], replace_source_id=pool[0]) == pool[1]
        # A stale contender cannot overwrite a newer binding.
        assert await retained.claim(pool[0], replace_source_id=pool[0]) == pool[1]
        assert await retained.owner() == pool[1]


@pytest.mark.parametrize("kind", ["thinking", "redacted_thinking"])
def test_thinking_does_not_require_account_owner(kind):
    assert not resource_ids({"messages": [{"role": "assistant", "content": [{"type": kind}]}]})


@pytest.mark.parametrize("kind", ["server_tool_use", "web_search_tool_result"])
def test_native_server_state_requires_owner(kind):
    assert resource_ids(
        {"messages": [{"role": "assistant", "content": [{"type": kind, "id": "srv1", "tool_use_id": "srv1"}]}]}
    ) == {"srv1"}
    assert not resource_ids({"messages": [{"role": "user", "content": [{"type": "tool_result"}]}]})
