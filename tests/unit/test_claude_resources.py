import pytest

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.resources import resource_ids
from app.modules.claude.wire_identity import native_conversation_id


@pytest.mark.parametrize(
    "value",
    [
        {"container": "container123"},
        {"content": [{"type": "document", "source": {"type": "file", "file_id": "file123"}}]},
        {"content": [{"type": "server_tool_use"}]},
        {"content": [{"type": "web_search_tool_result", "tool_use_id": ""}]},
    ],
)
def test_unknown_resource_shapes_fail_explicitly(value):
    with pytest.raises(ClaudeError):
        resource_ids(value)


def test_resource_replay_needs_stable_session():
    with pytest.raises(ClaudeError, match="explicit session"):
        native_conversation_id({"messages": [{"content": [{"type": "server_tool_use", "id": "srv1"}]}]}, {})


def test_scanner_does_not_interpret_custom_tool_data():
    assert not resource_ids(
        {
            "messages": [
                {
                    "content": [
                        {"type": "tool_use", "input": {"file_id": "user-supplied"}},
                        {"type": "tool_result", "content": [{"file_id": "user-supplied"}]},
                    ]
                }
            ]
        }
    )


def test_file_reference_in_native_tool_result_is_not_portable():
    with pytest.raises(ClaudeError, match="file/container"):
        resource_ids(
            {
                "messages": [
                    {
                        "content": [
                            {
                                "type": "tool_result",
                                "content": [{"type": "image", "source": {"type": "file", "file_id": "file123"}}],
                            }
                        ]
                    }
                ]
            }
        )
