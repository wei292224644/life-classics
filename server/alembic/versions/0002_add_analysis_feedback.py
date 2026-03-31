"""add analysis feedback table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-31 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("food_id", sa.BigInteger(), sa.ForeignKey("foods.id"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("client_context", postgresql.JSONB(), nullable=True),
        sa.Column("reporter_user_id", postgresql.UUID(), nullable=True),
        sa.Column("source_ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_analysis_feedback_food_id", "analysis_feedback", ["food_id"]
    )
    op.create_index(
        "ix_analysis_feedback_task_id", "analysis_feedback", ["task_id"]
    )


def downgrade() -> None:
    op.drop_table("analysis_feedback")
