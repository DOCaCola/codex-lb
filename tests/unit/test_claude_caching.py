import json
from copy import deepcopy

import pytest

from app.modules.claude.caching import cache_translated
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
    assert body["messages"][1] == signed
    once = deepcopy(body)
    cache_translated(body)
    assert body == once


def test_synthesized_identity_is_stable_scoped_and_not_a_provider_account():
    def make(source="a", client="client", conversation="conversation"):
        profile = RequestProfile.create(
            version="2.1.283", source_id=source, client_scope=client, conversation_id=conversation, native=False
        )
        body = {"metadata": {"other": "preserved"}}
        project_session(body, profile, source_id=source, client_scope=client, synthesize=True)
        identity = json.loads(body["metadata"]["user_id"])
        assert identity["session_id"] == profile.session_id
        assert identity["account_uuid"] == ""
        assert body["metadata"]["other"] == "preserved"
        return identity

    assert make() == make()
    assert make()["device_id"] == make(conversation="other")["device_id"]
    assert make()["session_id"] != make(conversation="other")["session_id"]
    assert make()["device_id"] != make(source="b")["device_id"]
    assert make()["device_id"] != make(client="other")["device_id"]
