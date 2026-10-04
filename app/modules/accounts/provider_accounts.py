"""Provider-account labels for usage grouped by Codex account or model source.

Codex usage carries ``account_id``; Claude, OpenRouter and other model-source
usage carries ``model_source_id`` instead. Callers outer-join ``Account`` and
``ModelSource`` on those columns and use these expressions for the label.
"""

from typing import Any, Literal

from sqlalchemy import case, func, literal
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import Account, ModelSource

AccountProvider = Literal["codex", "claude", "openrouter"]

# Source kinds with a dedicated brand; generic OpenAI-compatible sources have none.
BRANDED_SOURCE_KINDS = ("claude", "openrouter")


def provider_account_key(
    account_id: ColumnElement[Any] | InstrumentedAttribute[Any],
    model_source_id: ColumnElement[Any] | InstrumentedAttribute[Any],
) -> ColumnElement[str | None]:
    """One distinct identity per provider account; the namespaces keep source and account ids apart."""
    return func.coalesce(literal("source:") + model_source_id, literal("account:") + account_id)


def provider_account_name_expr() -> ColumnElement[str | None]:
    return func.coalesce(Account.alias, Account.email, ModelSource.name)


def provider_account_provider_expr() -> ColumnElement[str | None]:
    return case(
        (Account.id.is_not(None), literal("codex")),
        (ModelSource.kind.in_(BRANDED_SOURCE_KINDS), ModelSource.kind),
        else_=None,
    )
