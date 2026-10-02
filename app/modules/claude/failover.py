"""Request-wide send budget and persistent scoped upstream refusal policy."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Literal

from app.core.crypto import TokenEncryptor
from app.db.models import ClaudeCooldown
from app.db.session import get_background_session
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.auth import ClaudeAuth
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.quota_evidence import Evidence, Restriction, lock_account, read_evidence, save_evidence
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.routing import select_account
from app.modules.claude.schemas import AccountState
from app.modules.model_sources.forwarding import ModelSourceForwardingError

logger = logging.getLogger(__name__)


@dataclass
class SendBudget:
    remaining: int = 4
    requested_at: datetime | None = None

    def consume(self) -> None:
        if self.remaining <= 0:
            raise RuntimeError("Claude send budget exhausted before dispatch")
        self.remaining -= 1


@dataclass
class FailoverState:
    budget: SendBudget = field(default_factory=SendBudget)
    excluded: set[str] = field(default_factory=set)
    source_id: str | None = None
    last_error: ModelSourceForwardingError | None = None
    stream_opened: bool = False
    credential_generation: int | None = None
    auth_retried: set[str] = field(default_factory=set)
    retry_source_id: str | None = None
    overload_retried: bool = False
    connect_retries: int = 0


def is_authentication_failure(error: ModelSourceForwardingError) -> bool:
    if error.upstream_status_code != 401:
        return False
    detail = error.payload.get("error")
    return isinstance(detail, dict) and detail.get("type") in (None, "authentication_error")


async def recover_authentication(
    state: FailoverState, model: str, api_key: ApiKeyData | None, *, reasoning_effort: str | None = None
) -> None:
    assert state.source_id is not None and state.credential_generation is not None
    source_id = state.source_id
    state.retry_source_id = None
    async with get_background_session() as session:
        repository = ClaudeRepository(session)
        if source_id in state.auth_retried:
            await repository.backoff_rejected_generation(
                source_id, state.credential_generation, datetime.now(UTC).replace(tzinfo=None)
            )
            state.excluded.add(source_id)
            logger.info("claude_auth_recovery source_id=%s outcome=rejected_again", source_id)
            return
        if state.budget.remaining == 0:
            return
        state.auth_retried.add(source_id)
        try:
            # Authorization and current eligibility still precede refresh.
            await select_account(
                session,
                model,
                api_key,
                conversation_id="",
                owner_source_id=source_id,
                reasoning_effort=reasoning_effort,
            )
            await ClaudeAuth(repository, ClaudeClient(), TokenEncryptor()).snapshot(
                source_id, rejected_generation=state.credential_generation
            )
        except ClaudeError:
            # Auth owns terminal/backoff/uncertain state. Never rewrite it here.
            state.excluded.add(source_id)
            logger.info("claude_auth_recovery source_id=%s outcome=unavailable", source_id)
            return
    state.retry_source_id = source_id
    logger.info("claude_auth_recovery source_id=%s outcome=reprepare", source_id)


@dataclass(frozen=True)
class Refusal:
    scope: Literal["account", "model"]
    until: datetime
    reason: Literal["retry_after", "reset", "default"]
    window: str = "unknown"


def _reset(raw: str | None, now: datetime) -> datetime | None:
    if raw is None:
        return None
    try:
        deadline = datetime.fromtimestamp(float(raw), UTC)
    except (ValueError, OverflowError, OSError):
        return None
    return deadline if deadline > now else None


def _retry_deadline(raw: str | None, now: datetime) -> datetime | None:
    if not raw:
        return None
    try:
        seconds = float(raw)
        deadline = now + timedelta(seconds=max(1, seconds)) if math.isfinite(seconds) else None
    except (ValueError, OverflowError):
        try:
            deadline = parsedate_to_datetime(raw).astimezone(UTC)
        except (ValueError, TypeError, OverflowError):
            return None
    return deadline if deadline is not None and deadline > now else None


def _utilization(headers: dict[str, str], window: str) -> float | None:
    try:
        value = float(headers.get(f"anthropic-ratelimit-unified-{window}-utilization", ""))
    except ValueError:
        return None
    return value if math.isfinite(value) and value >= 0 else None


def _shared_healthy(headers: dict[str, str]) -> bool:
    statuses = [headers.get(f"anthropic-ratelimit-unified-{window}-status", "") for window in ("5h", "7d")]
    allowed = {"allowed", "allowed_warning"}
    if all(status in allowed for status in statuses):
        return True
    for index, window in enumerate(("5h", "7d")):
        if statuses[index] or statuses[1 - index] not in allowed:
            continue
        value = _utilization(headers, window)
        if value is not None and value < 1:
            return True
    return False


def classify_refusals(error: ModelSourceForwardingError, *, now: datetime) -> tuple[Refusal, ...]:
    if error.upstream_status_code != 429:
        return ()
    detail = error.payload.get("error")
    message = detail.get("message") if isinstance(detail, dict) else None
    message = message.lower() if isinstance(message, str) else ""
    if "fast request rejected" in message or (
        "fast" in message and ("usage credits" in message or "credits are required" in message)
    ):
        return ()
    headers = {key.lower(): value.strip().lower() for key, value in error.upstream_headers.items()}
    prefix = "anthropic-ratelimit-unified"
    shared = [window for window in ("5h", "7d") if headers.get(f"{prefix}-{window}-status") == "rejected"]
    unified = headers.get(f"{prefix}-status") == "rejected"
    claim = headers.get(f"{prefix}-representative-claim", "")
    model_usage = _utilization(headers, "7d_oi")
    model_window_rejected = headers.get(f"{prefix}-7d_oi-status") == "rejected" or (
        model_usage is not None and model_usage >= 1
    )
    model_signal = (
        model_window_rejected
        or headers.get(f"{prefix}-overage-status") == "rejected"
        or bool(headers.get(f"{prefix}-overage-disabled-reason"))
        or "overage" in claim
    )
    details = detail.get("details") if isinstance(detail, dict) else None
    entitlement = isinstance(details, dict) and details.get("error_code") == "credits_required"
    model_only = entitlement or (model_signal and _shared_healthy(headers))
    account_limited = bool(shared) or (unified and not model_only)
    model_limited = entitlement or model_signal or not account_limited

    # Retry-After describes the binding claim, not every window in a mixed refusal.
    claim_scope = "model" if "overage" in claim else "account" if claim in {"five_hour", "seven_day"} else None
    if claim_scope is None and account_limited != model_limited:
        claim_scope = "account" if account_limited else "model"
    retry = _retry_deadline(error.retry_after or headers.get("retry-after"), now)
    aggregate = _reset(headers.get(f"{prefix}-reset"), now)
    restrictions: list[Refusal] = []
    for scope, limited, windows in (
        ("account", account_limited, shared),
        ("model", model_limited, ["7d_oi"] if model_window_rejected else []),
    ):
        if not limited:
            continue
        for window in windows or ["unknown"]:
            name = {"5h": "five_hour", "7d": "seven_day", "7d_oi": "seven_day_overage_included"}.get(window, "unknown")
            if scope == "model" and entitlement:
                name = "entitlement"
            if name == "unknown" and claim in {"five_hour", "seven_day"} and scope == "account":
                name = claim
            if window == "unknown" and scope == "model" and "overage" in claim and not entitlement:
                name = "seven_day_overage_included"
            reset = _reset(headers.get(f"{prefix}-{window}-reset"), now)
            attributable = claim_scope == scope and (len(windows) <= 1 or claim == name)
            if attributable and retry is not None:
                restrictions.append(Refusal(scope, max(retry, reset or retry), "retry_after", name))
            elif reset is not None or (attributable and aggregate is not None):
                deadline = reset or aggregate
                assert deadline is not None
                restrictions.append(Refusal(scope, deadline, "reset", name))
            else:
                restrictions.append(Refusal(scope, now + timedelta(seconds=60), "default", name))
    return tuple(restrictions)


async def record_refusals(
    source_id: str,
    model: str,
    refusals: tuple[Refusal, ...],
    *,
    requested_at: datetime | None = None,
) -> None:
    now = datetime.now(UTC)
    requested_at = requested_at or now
    async with get_background_session() as session:
        account = await lock_account(session, source_id)
        state = AccountState.model_validate_json(account.state_json)
        for refusal in refusals:
            if refusal.until <= now:
                continue
            barrier = state.reset_barriers.get(refusal.window)
            if barrier is not None and requested_at <= barrier:
                continue
            key = "*" if refusal.scope == "account" else model
            row = await session.get(ClaudeCooldown, (source_id, key))
            evidence = read_evidence(row) if row is not None else Evidence()
            if row is None:
                row = ClaudeCooldown(source_id=source_id, model=key, until=refusal.until.replace(tzinfo=None))
                session.add(row)
            evidence.restrictions.append(
                Restriction(
                    window=refusal.window,
                    until=refusal.until,
                    requested_at=requested_at,
                )
            )
            await save_evidence(session, row, evidence, now)
            await session.flush()
        await session.commit()
    for refusal in refusals:
        logger.info("claude_refusal source_id=%s scope=%s cooldown=%s", source_id, refusal.scope, refusal.reason)
