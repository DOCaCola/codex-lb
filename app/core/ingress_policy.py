"""Process-owned Responses admission budget, shared by transports and replay."""

from app.core.config.settings import get_settings


def responses_body_limit_bytes() -> int:
    return get_settings().responses_body_limit_bytes
