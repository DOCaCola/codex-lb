"""Local admission refusal, distinct from provider failures and send retries."""

from app.modules.model_sources.forwarding import ModelSourceForwardingError


class ClaudeCapacityBusy(ModelSourceForwardingError):
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        super().__init__(
            status_code=503,
            payload={
                "error": {
                    "type": "server_error",
                    "code": "model_source_busy",
                    "message": "Claude account concurrency capacity is busy; retry shortly.",
                }
            },
            retry_after="1",
        )
