from __future__ import annotations

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app import cli
from app.core import ingress_policy
from app.core.config.settings import Settings, get_settings
from app.core.middleware.request_body_limit import request_body_limit_for_path
from app.modules.proxy._service import response_create

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", [32, 128, 256, 512])
def test_instance_budget_reaches_all_consumers(monkeypatch, value):
    budget = value * 1024 * 1024
    monkeypatch.setenv("CODEX_LB_RESPONSES_BODY_LIMIT_BYTES", str(budget))
    get_settings.cache_clear()
    try:
        assert ingress_policy.responses_body_limit_bytes() == budget
        assert response_create.responses_body_limit_bytes() == budget
        assert request_body_limit_for_path("/internal/bridge/responses") == budget
        for prefix in ("/v1", "/backend-api/codex"):
            for suffix in ("/responses", "/responses/compact"):
                for trailing in ("", "/"):
                    assert request_body_limit_for_path(prefix + suffix + trailing) == budget
        assert request_body_limit_for_path("/v1/chat/completions") == 32 * 1024 * 1024
        assert request_body_limit_for_path("/v1/responses/compact/other") == 32 * 1024 * 1024
        run = Mock()
        monkeypatch.delenv("UVICORN_WS_MAX_SIZE", raising=False)
        monkeypatch.setattr(cli, "_run_server", run)
        cli.main([])
        assert run.call_args.kwargs["ws_max_size"] == budget
        cli.main(["--ws-max-size", "33554432"])
        assert run.call_args.kwargs["ws_max_size"] == 32 * 1024 * 1024
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("value", ["0", "-1", "33554431", "536870913", "1.5", "unlimited", "NaN"])
def test_invalid_budget_fails_configuration(monkeypatch, value):
    monkeypatch.setenv("CODEX_LB_RESPONSES_BODY_LIMIT_BYTES", value)
    with pytest.raises(ValidationError, match="responses_body_limit_bytes"):
        Settings(_env_file=None)


def test_budget_default_and_restart_contract(monkeypatch):
    monkeypatch.delenv("CODEX_LB_RESPONSES_BODY_LIMIT_BYTES", raising=False)
    get_settings.cache_clear()
    try:
        assert ingress_policy.responses_body_limit_bytes() == 128 * 1024 * 1024
        monkeypatch.setenv("CODEX_LB_RESPONSES_BODY_LIMIT_BYTES", "268435456")
        assert ingress_policy.responses_body_limit_bytes() == 128 * 1024 * 1024
        get_settings.cache_clear()
        assert ingress_policy.responses_body_limit_bytes() == 256 * 1024 * 1024
    finally:
        get_settings.cache_clear()
