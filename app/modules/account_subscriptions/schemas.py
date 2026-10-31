from __future__ import annotations

from datetime import datetime

from pydantic import AwareDatetime

from app.modules.shared.schemas import DashboardModel


class AccountSubscriptionEndResponse(DashboardModel):
    account_id: str | None
    model_source_id: str | None
    ends_at: datetime


class AccountSubscriptionEndsResponse(DashboardModel):
    ends: list[AccountSubscriptionEndResponse]


class AccountSubscriptionEndUpdate(DashboardModel):
    ends_at: AwareDatetime | None
