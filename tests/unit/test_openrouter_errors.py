import json

import pytest

from app.modules.openrouter.errors import MAX_ERROR_MESSAGE, normalize_error

pytestmark = pytest.mark.unit


def test_nested_diagnostics_are_allowlisted_and_redacted_before_truncation():
    secret = "plain-configured-secret"
    payload = {
        "debug": "private debug",
        "error": {
            "message": "Provider returned error " + secret,
            "code": 400,
            "metadata": {
                "provider_name": "Example",
                "headers": {"Authorization": "private-header"},
                "raw": json.dumps(
                    {
                        "error": {
                            "message": "Missing reasoning; key sk-or-v1-abc***def; Bearer other-secret",
                            "code": "invalid_request",
                            "param": "messages[2].reasoning",
                            "request": "private prompt",
                        }
                    }
                ),
            },
        },
    }
    result = normalize_error(payload, 400, secret=secret)
    encoded = json.dumps(result)
    for value in [secret, "abc", "def", "other-secret", "private-header", "private prompt", "private debug"]:
        assert value not in encoded
    message = result["error"]["message"]
    assert "Missing reasoning" in message
    assert "provider: Example" in message
    assert "param=messages[2].reasoning" in message
    assert "metadata" not in result["error"]
    long = normalize_error({"error": {"message": "x" * 1015 + secret}}, 400, secret=secret)
    assert "plain-" not in json.dumps(long)
    assert len(message) <= MAX_ERROR_MESSAGE


@pytest.mark.parametrize(
    "raw", ["non-json private prompt", ["private"], None, "{" + "x" * 70000, "[" * 10000 + "]" * 10000]
)
def test_unstructured_metadata_is_not_echoed(raw):
    result = normalize_error({"error": {"message": "Provider returned error", "metadata": {"raw": raw}}}, 400)
    assert result["error"]["message"] == "Provider returned error"
