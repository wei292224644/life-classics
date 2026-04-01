"""drop ingredient_analyses.version

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-01 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("ingredient_analyses", "version")


def downgrade() -> None:
    op.add_column(
        "ingredient_analyses",
        sa.Column("version", sa.String(50), nullable=False, server_default="v1"),
    )
