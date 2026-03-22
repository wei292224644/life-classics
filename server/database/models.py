"""
SQLAlchemy ORM 模型，映射现有 PostgreSQL 表结构。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


# ── 枚举类型（匹配 PostgreSQL enum）───────────────────────────────────────

who_level_enum = PG_ENUM(
    "Group 1", "Group 2A", "Group 2B", "Group 3", "Group 4", "Unknown",
    name="who_level",
    create_type=False,
)

reference_unit_enum = PG_ENUM(
    "g", "mg", "kcal", "mL", "kJ", "serving", "day",
    name="reference_unit",
    create_type=False,
)

unit_enum = PG_ENUM(
    "g", "mg", "kcal", "mL", "kJ",
    name="unit",
    create_type=False,
)

reference_type_enum = PG_ENUM(
    "PER_100_WEIGHT", "PER_100_ENERGY", "PER_SERVING", "PER_DAY",
    name="reference_type",
    create_type=False,
)

analysis_target_enum = PG_ENUM(
    "food", "ingredient",
    name="analysis_target",
    create_type=False,
)

analysis_type_enum = PG_ENUM(
    "usage_advice_summary", "health_summary", "pregnancy_safety",
    "risk_summary", "recent_risk_summary", "ingredient_summary",
    name="analysis_type",
    create_type=False,
)

analysis_version_enum = PG_ENUM(
    "v1",
    name="analysis_version",
    create_type=False,
)

level_enum = PG_ENUM(
    "t4", "t3", "t2", "t1", "t0", "unknown",
    name="level",
    create_type=False,
)

iarc_agent_group_enum = PG_ENUM(
    "1", "2A", "2B", "3", "unknown",
    name="iarc_agent_group",
    create_type=False,
)

iarc_agent_link_type_enum = PG_ENUM(
    "see", "see_also",
    name="iarc_agent_link_type",
    create_type=False,
)


# ── 公共列Mixin ────────────────────────────────────────────────────────────

class TimestampMixin:
    """时间戳和软删除字段"""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── 食品表 ─────────────────────────────────────────────────────────────────

class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    barcode: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url_list: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    production_address: Mapped[str | None] = mapped_column(String(255))
    origin_place: Mapped[str | None] = mapped_column(String(255))
    production_license: Mapped[str | None] = mapped_column(String(255))
    product_category: Mapped[str | None] = mapped_column(String(255))
    product_standard_code: Mapped[str | None] = mapped_column(String(255))
    shelf_life: Mapped[str | None] = mapped_column(String(100))
    net_content: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    food_ingredients: Mapped[list[FoodIngredient]] = relationship(
        back_populates="food", lazy="selectin"
    )
    food_nutrition_entries: Mapped[list[FoodNutritionEntry]] = relationship(
        back_populates="food", lazy="selectin"
    )


# ── 配料表 ─────────────────────────────────────────────────────────────────

class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    description: Mapped[str | None] = mapped_column(Text)
    is_additive: Mapped[bool] = mapped_column(Boolean, default=False)
    additive_code: Mapped[str | None] = mapped_column(String(50))
    standard_code: Mapped[str | None] = mapped_column(String(255))
    who_level: Mapped[str | None] = mapped_column(who_level_enum, default="Unknown")
    allergen_info: Mapped[str | None] = mapped_column(String(255))
    function_type: Mapped[str | None] = mapped_column(String(100))
    origin_type: Mapped[str | None] = mapped_column(String(100))
    limit_usage: Mapped[str | None] = mapped_column(String(255))
    legal_region: Mapped[str | None] = mapped_column(String(255))
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    food_ingredients: Mapped[list[FoodIngredient]] = relationship(
        back_populates="ingredient", lazy="selectin"
    )


# ── 食品-配料关联表 ─────────────────────────────────────────────────────────

class FoodIngredient(Base):
    __tablename__ = "food_ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("foods.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ingredients.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    food: Mapped[Food] = relationship(back_populates="food_ingredients")
    ingredient: Mapped[Ingredient] = relationship(back_populates="food_ingredients")


# ── 营养成分表 ─────────────────────────────────────────────────────────────

class NutritionTable(Base):
    __tablename__ = "nutrition_table"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    category: Mapped[str | None] = mapped_column(String(255))
    sub_category: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    daily_value: Mapped[str | None] = mapped_column(String(255))
    upper_limit: Mapped[str | None] = mapped_column(String(255))
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_info: Mapped[str | None] = mapped_column(Text)
    pregnancy_note: Mapped[str | None] = mapped_column(Text)
    metabolism_role: Mapped[str | None] = mapped_column(String(255))
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    food_nutrition_entries: Mapped[list[FoodNutritionEntry]] = relationship(
        back_populates="nutrition", lazy="selectin"
    )


# ── 食品营养值表 ───────────────────────────────────────────────────────────

class FoodNutritionEntry(Base):
    __tablename__ = "food_nutrition_table"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("foods.id"), nullable=False)
    nutrition_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("nutrition_table.id"), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    value_unit: Mapped[str] = mapped_column(unit_enum, nullable=False)
    reference_type: Mapped[str] = mapped_column(reference_type_enum, nullable=False)
    reference_unit: Mapped[str] = mapped_column(reference_unit_enum, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    food: Mapped[Food] = relationship(back_populates="food_nutrition_entries")
    nutrition: Mapped[NutritionTable] = relationship(back_populates="food_nutrition_entries")


# ── 分析详情表（通用分析结果）──────────────────────────────────────────────

class AnalysisDetail(Base):
    __tablename__ = "analysis_details"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # food_id 或 ingredient_id
    analysis_target: Mapped[str] = mapped_column(analysis_target_enum, nullable=False)  # 'food' or 'ingredient'
    analysis_type: Mapped[str] = mapped_column(analysis_type_enum, nullable=False)
    analysis_version: Mapped[str] = mapped_column(analysis_version_enum, nullable=False)
    ai_model: Mapped[str] = mapped_column(String(255), nullable=False)
    results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    level: Mapped[str] = mapped_column(level_enum, nullable=False, default="unknown")
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)



# ── IARC 致癌物表 ─────────────────────────────────────────────────────────

class IarcAgent(Base):
    __tablename__ = "iarc_agents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cas_no: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    zh_agent_name: Mapped[str | None] = mapped_column(String(255))
    group: Mapped[str] = mapped_column(iarc_agent_group_enum, nullable=False)
    volume: Mapped[str] = mapped_column(String(255), nullable=False)
    volume_publication_year: Mapped[str] = mapped_column(String(255), nullable=False)
    evaluation_year: Mapped[str] = mapped_column(String(255), nullable=False)
    additional_information: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IarcCancerSite(Base):
    __tablename__ = "iarc_cancer_sites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zh_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    sufficient_evidence_agents: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    limited_evidence_agents: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IarcAgentLink(Base):
    __tablename__ = "iarc_agent_links"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    from_agent_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("iarc_agents.id"), nullable=False)
    to_agent_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("iarc_agents.id"), nullable=False)
    link_type: Mapped[str] = mapped_column(iarc_agent_link_type_enum, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user: Mapped[str] = mapped_column(Uuid, nullable=False)
    last_updated_by_user: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    from_agent: Mapped[IarcAgent] = relationship(IarcAgent, foreign_keys=[from_agent_id])
    to_agent: Mapped[IarcAgent] = relationship(IarcAgent, foreign_keys=[to_agent_id])
