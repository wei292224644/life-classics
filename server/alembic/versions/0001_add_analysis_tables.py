"""add analysis tables

Revision ID: 0001
Revises:
Create Date: 2026-03-31 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ingredient_analyses ───────────────────────────────────────────────────
    # append-only 设计：ingredient_id 无 UNIQUE 约束，允许多历史行
    # is_active=True 标记当前有效行
    op.create_table(
        "ingredient_analyses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ingredient_id", sa.BigInteger(), sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("ai_model", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "level",
            postgresql.ENUM(
                "t4", "t3", "t2", "t1", "t0", "unknown",
                name="level",
                create_type=False,  # enum 已存在
            ),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("safety_info", sa.Text(), nullable=False, server_default=""),
        sa.Column("alternatives", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("decision_trace", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_user", postgresql.UUID(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_updated_by_user", postgresql.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ingredient_analyses_ingredient_id", "ingredient_analyses", ["ingredient_id"])
    op.create_index("ix_ingredient_analyses_is_active", "ingredient_analyses", ["is_active"])

    # ── product_analyses ──────────────────────────────────────────────────────
    # 本版首写即缓存：food_id UNIQUE，一个 food_id 只允许一行
    op.create_table(
        "product_analyses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("food_id", sa.BigInteger(), sa.ForeignKey("foods.id"), nullable=False, unique=True),
        sa.Column("ai_model", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "level",
            postgresql.ENUM(
                "t4", "t3", "t2", "t1", "t0", "unknown",
                name="level",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("advice", sa.Text(), nullable=False),
        sa.Column("demographics", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("scenarios", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("references", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_user", postgresql.UUID(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_updated_by_user", postgresql.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_product_analyses_food_id", "product_analyses", ["food_id"])


def downgrade() -> None:
    op.drop_table("product_analyses")
    op.drop_table("ingredient_analyses")
