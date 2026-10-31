from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import and_, or_

from app.db.models import RequestLog

_INTERNAL_LIMIT_WARMUP_SOURCE = "limit_warmup"
_INTERNAL_WARMUP_REQUEST_KINDS = ("warmup", "limit_warmup")
MISSING_USERAGENT_GROUP = "Missing User-Agent"


def _values(values: Iterable[str] | None) -> tuple[str, ...]:
    return tuple(sorted({value for value in values or () if value}))


@dataclass(frozen=True)
class ReportFilters:
    """Report selection: values within a dimension match any, dimensions combine with AND.

    Codex usage is attributed by ``account_id``, provider-account usage by
    ``model_source_id``; a row matches the account selection through either.
    """

    account_ids: tuple[str, ...] = ()
    model_source_ids: tuple[str, ...] = ()
    api_key_ids: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    useragent_groups: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        account_ids: Iterable[str] | None = None,
        model_source_ids: Iterable[str] | None = None,
        api_key_ids: Iterable[str] | None = None,
        models: Iterable[str] | None = None,
        useragent_groups: Iterable[str] | None = None,
    ) -> ReportFilters:
        return cls(
            _values(account_ids),
            _values(model_source_ids),
            _values(api_key_ids),
            _values(models),
            _values(useragent_groups),
        )

    def without_selection(self) -> ReportFilters:
        """Scope of the model and user-agent catalogs: accounts and API keys only."""
        return replace(self, models=(), useragent_groups=())

    def api_keys_only(self) -> ReportFilters:
        """Scope of the account catalog, which must not narrow itself."""
        return ReportFilters(api_key_ids=self.api_key_ids)

    def conditions(
        self,
        *,
        account_id: Any,
        model_source_id: Any,
        api_key_id: Any,
        model: Any,
        useragent_group: Any,
        encode: Callable[[str | None], str] | None = None,
    ) -> list:
        """Predicates over raw columns, or over rollup columns stored through ``encode``."""

        def stored(values: Iterable[str]) -> list[str]:
            return [encode(value) for value in values] if encode else list(values)

        conditions = []
        if self.account_ids or self.model_source_ids:
            conditions.append(
                or_(
                    *([account_id.in_(stored(self.account_ids))] if self.account_ids else []),
                    *([model_source_id.in_(stored(self.model_source_ids))] if self.model_source_ids else []),
                )
            )
        if self.api_key_ids:
            conditions.append(api_key_id.in_(stored(self.api_key_ids)))
        if self.models:
            conditions.append(model.in_(self.models))
        if self.useragent_groups:
            named = [group for group in self.useragent_groups if group != MISSING_USERAGENT_GROUP]
            missing = MISSING_USERAGENT_GROUP in self.useragent_groups
            if encode:
                conditions.append(useragent_group.in_([*stored(named), *([encode(None)] if missing else [])]))
            else:
                conditions.append(
                    or_(
                        *([useragent_group.is_(None)] if missing else []),
                        *([useragent_group.in_(named)] if named else []),
                    )
                )
        return conditions

    def request_log_conditions(self) -> list:
        return self.conditions(
            account_id=RequestLog.account_id,
            model_source_id=RequestLog.model_source_id,
            api_key_id=RequestLog.api_key_id,
            model=RequestLog.model,
            useragent_group=RequestLog.useragent_group,
        )


def _normal_traffic_clause():
    return and_(
        or_(RequestLog.source.is_(None), RequestLog.source != _INTERNAL_LIMIT_WARMUP_SOURCE),
        or_(
            RequestLog.request_kind.is_(None),
            RequestLog.request_kind.not_in(_INTERNAL_WARMUP_REQUEST_KINDS),
        ),
    )
