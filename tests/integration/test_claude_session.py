from datetime import timedelta

import pytest

from app.core.utils.time import utcnow
from app.db.models import ClaudeSessionOwner
from app.db.session import SessionLocal
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.session import NATIVE_SESSION_TTL, NativeSessionOwnership, contains_account_bound_state
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
        assert await retained.owner(required=True) == pool[0]
        assert await retained.claim(pool[1]) == pool[0]
        row = await session.get(ClaudeSessionOwner, retained.key)
        assert row is not None
        assert utcnow() < row.expires_at <= utcnow() + NATIVE_SESSION_TTL
    async with SessionLocal() as session:
        assert await owner(session, client="another").owner(required=False) is None
        assert await owner(session, conversation="another").owner(required=False) is None
        assert await owner(session, model="anthropic/claude-sonnet-5").owner(required=False) is None


async def test_expired_owner_requires_portable_context(pool):
    async with SessionLocal() as session:
        retained = owner(session)
        await retained.claim(pool[0])
        row = await session.get(ClaudeSessionOwner, retained.key)
        assert row is not None
        row.expires_at = utcnow() - timedelta(seconds=1)
        await session.commit()
    async with SessionLocal() as session:
        retained = owner(session)
        with pytest.raises(ClaudeError, match="no retained account owner"):
            await retained.owner(required=True)
        assert await retained.owner(required=False) is None
        assert await retained.claim(pool[1]) == pool[1]


@pytest.mark.parametrize("kind", ["thinking", "redacted_thinking", "server_tool_use", "web_search_tool_result"])
def test_native_server_state_requires_owner(kind):
    assert contains_account_bound_state({"messages": [{"role": "assistant", "content": [{"type": kind}]}]})
    assert not contains_account_bound_state({"messages": [{"role": "user", "content": [{"type": "tool_result"}]}]})
