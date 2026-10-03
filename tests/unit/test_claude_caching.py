import json
from copy import deepcopy

import pytest

from app.modules.claude.caching import cache_translated, retain_thinking
from app.modules.claude.profile import RequestProfile
from app.modules.claude.wire_identity import project_session

pytestmark = pytest.mark.unit


def test_translated_cache_markers_do_not_touch_signed_server_blocks():
    body = {
        "system": [{"type": "text", "text": "Instructions"}],
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "First"}]},
            {
                "role": "assistant",
                "content": [
                    {"type": "server_tool_use", "id": "server"},
                    {"type": "web_search_tool_result", "content": []},
                ],
            },
            {"role": "user", "content": [{"type": "text", "text": "Second"}]},
        ],
    }
    signed = deepcopy(body["messages"][1])
    cache_translated(body)
    assert json.dumps(body).count('"cache_control"') == 3
    # Claude Code's own TTL: tool and review pauses outlast a 5-minute entry.
    assert [
        block["cache_control"] for block in (body["system"][-1], *(m["content"][-1] for m in body["messages"][::2]))
    ] == [{"type": "ephemeral", "ttl": "1h"}] * 3
    assert body["messages"][1] == signed
    once = deepcopy(body)
    cache_translated(body)
    assert body == once


@pytest.mark.parametrize(
    "thinking,retained",
    [
        ({"type": "adaptive"}, True),
        ({"type": "enabled", "budget_tokens": 4096}, True),
        ({"type": "disabled"}, False),
        (None, False),
    ],
)
def test_earlier_turn_thinking_is_kept_only_when_thinking_is_on(thinking, retained):
    body = {"messages": []} if thinking is None else {"messages": [], "thinking": thinking}
    assert retain_thinking(body) is retained
    if retained:
        # Claude Code's value: the default strips earlier-turn thinking and
        # moves the cached prefix at every new user turn.
        assert body["context_management"] == {"edits": [{"type": "clear_thinking_20251015", "keep": "all"}]}
    else:
        assert "context_management" not in body


def test_synthesized_identity_is_stable_scoped_and_names_the_serving_account():
    def make(source="a", client="client", conversation="conversation"):
        profile = RequestProfile.create(
            version="2.1.283", source_id=source, client_scope=client, conversation_id=conversation, native=False
        )
        body = {"metadata": {"other": "preserved"}}
        project_session(
            body, profile, source_id=source, account_uuid=f"uuid-{source}", client_scope=client, synthesize=True
        )
        identity = json.loads(body["metadata"]["user_id"])
        assert identity["session_id"] == profile.session_id
        assert identity["account_uuid"] == f"uuid-{source}"
        assert body["metadata"]["other"] == "preserved"
        return identity

    assert make() == make()
    assert make()["device_id"] == make(conversation="other")["device_id"]
    assert make()["session_id"] != make(conversation="other")["session_id"]
    assert make()["device_id"] != make(source="b")["device_id"]
    assert make()["device_id"] != make(client="other")["device_id"]
