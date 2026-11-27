"""one operator name per published model

Revision ID: 20261127_000000_model_display_names
Revises: 20261126_010000_utc_openrouter_state_timestamps
Create Date: 2026-11-27

Adds ``model_display_names``: the operator's name for a published model slug,
set in the Settings model catalogue for every provider. The names OpenRouter and
OpenAI API account selections and generic OpenAI-compatible source models
carried move there; where two accounts named one model differently, the first
account's name is kept.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "20261127_000000_model_display_names"
down_revision = "20261126_010000_utc_openrouter_state_timestamps"
branch_labels = None
depends_on = None

_TABLE = "model_display_names"
# Account tables whose selections carried a name, with the prefix their models publish under.
_SELECTION_ACCOUNTS = (("openrouter_accounts", "openrouter/"), ("openai_api_accounts", "openai-apikey/"))


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("slug"),
        )
    names: dict[str, str] = {}
    for table_name, prefix in _SELECTION_ACCOUNTS:
        accounts = sa.table(table_name, sa.column("source_id", sa.String()), sa.column("state_json", sa.Text()))
        rows = bind.execute(sa.select(accounts.c.source_id, accounts.c.state_json).order_by(accounts.c.source_id))
        for source_id, stored in rows.all():
            state = json.loads(stored)
            named = [selection for selection in state.get("selections", []) if "display_name" in selection]
            if not named:
                continue
            for selection in named:
                name = selection.pop("display_name")
                if name and name.strip():
                    names.setdefault(prefix + selection["model"], name.strip())
            bind.execute(
                accounts.update().where(accounts.c.source_id == source_id).values(state_json=json.dumps(state))
            )
    sources = sa.table("model_sources", sa.column("id", sa.String()), sa.column("kind", sa.String()))
    models = sa.table(
        "model_source_models",
        sa.column("id", sa.Integer()),
        sa.column("source_id", sa.String()),
        sa.column("model", sa.String()),
        sa.column("display_name", sa.String()),
    )
    generic = bind.execute(
        sa.select(models.c.id, models.c.model, models.c.display_name)
        .join(sources, sources.c.id == models.c.source_id)
        .where(sources.c.kind == "openai_compatible", models.c.display_name.is_not(None))
        .order_by(models.c.source_id, models.c.id)
    ).all()
    for model_id, model, name in generic:
        if name.strip() and name.strip() != model:
            names.setdefault(model, name.strip())
        bind.execute(models.update().where(models.c.id == model_id).values(display_name=None))
    if names:
        table = sa.table(_TABLE, sa.column("slug", sa.String()), sa.column("display_name", sa.String()))
        existing = set(bind.execute(sa.select(table.c.slug)).scalars())
        rows = [{"slug": slug, "display_name": name} for slug, name in names.items() if slug not in existing]
        if rows:
            bind.execute(table.insert(), rows)


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(_TABLE):
        op.drop_table(_TABLE)
