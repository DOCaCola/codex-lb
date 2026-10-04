from __future__ import annotations

from pydantic import Field

from app.modules.account_colors.service import PALETTE_SIZE
from app.modules.shared.schemas import DashboardModel


class AccountColorResponse(DashboardModel):
    account_id: str | None
    model_source_id: str | None
    chart_color: int | None
    color: int
    automatic_color: int


class AccountColorsResponse(DashboardModel):
    colors: list[AccountColorResponse]


class AccountColorUpdate(DashboardModel):
    chart_color: int | None = Field(ge=0, lt=PALETTE_SIZE)
