from __future__ import annotations

from datetime import UTC, datetime

from app.core.errors import OpenAIErrorDetail
from app.core.types import JsonValue


class AntigravityError(ValueError):
    """Public diagnostic; never contains tokens or raw upstream auth bodies."""

    code = "antigravity_invalid_request"
    status_code = 400

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code

    @property
    def response_headers(self) -> dict[str, str]:
        return {}

    @property
    def error_type(self) -> str:
        return "invalid_request_error" if self.status_code == 400 else "server_error"

    @property
    def responses_error_detail(self) -> OpenAIErrorDetail:
        return {"type": self.error_type, "code": self.code, "message": str(self)}


class TokenRejected(AntigravityError):
    """Google refused a refresh; terminal means the grant is gone (invalid_grant)."""

    def __init__(self, message: str, *, terminal: bool) -> None:
        super().__init__(message, code="antigravity_token_rejected")
        self.terminal = terminal


class MetadataHTTPError(AntigravityError):
    def __init__(self, endpoint: str, status: int, retry_at: datetime | None = None, *, body: JsonValue = None) -> None:
        super().__init__(
            f"Antigravity {endpoint} returned HTTP {status}", code="antigravity_metadata_failed", status_code=502
        )
        self.status = status
        self.retry_at = retry_at or datetime.now(UTC)
        # The parsed google.rpc error, for classification only; never shown.
        self.body = body
