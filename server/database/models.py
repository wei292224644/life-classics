"""
SQLAlchemy ORM 模型，映射现有 PostgreSQL 表。
只做映射，不做 DDL（表结构已由 Drizzle 管理）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    barcode: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String)
    origin_place: Mapped[str | None] = mapped_column(String)
    shelf_life: Mapped[str | None] = mapped_column(String)
    net_content: Mapped[str | None] = mapped_column(String)
    image_url_list: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    food_ingredients: Mapped[list[FoodIngredient]] = relationship(
        back_populates="food", lazy="selectin"
    )
    food_nutrition_entries: Mapped[list[FoodNutritionEntry]] = relationship(
        back_populates="food", lazy="selectin"
    )
    analysis_details: Mapped[list[AnalysisDetail]] = relationship(
        back_populates="food", lazy="selectin"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    alias: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    is_additive: Mapped[bool] = mapped_column(Boolean, default=False)
    additive_code: Mapped[str | None] = mapped_column(String)
    who_level: Mapped[str | None] = mapped_column(String)
    allergen_info: Mapped[str | None] = mapped_column(Text)
    function_type: Mapped[str | None] = mapped_column(String)
    standard_code: Mapped[str | None] = mapped_column(String)

    food_ingredients: Mapped[list[FoodIngredient]] = relationship(
        back_populates="ingredient", lazy="selectin"
    )
    analysis_details: Mapped[list[AnalysisDetail]] = relationship(
        back_populates="ingredient", lazy="selectin"
    )


class FoodIngredient(Base):
    __tablename__ = "food_ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("foods.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingredients.id"), nullable=False
    )
    order_index: Mapped[int | None] = mapped_column(Integer)

    food: Mapped[Food] = relationship(back_populates="food_ingredients")
    ingredient: Mapped[Ingredient] = relationship(back_populates="food_ingredients")


class NutritionTable(Base):
    __tablename__ = "nutrition_table"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    alias: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    daily_value: Mapped[Any | None] = mapped_column(Numeric)
    daily_value_unit: Mapped[str | None] = mapped_column(String)
    risk_info: Mapped[str | None] = mapped_column(Text)
    pregnancy_note: Mapped[str | None] = mapped_column(Text)

    food_nutrition_entries: Mapped[list[FoodNutritionEntry]] = relationship(
        back_populates="nutrition", lazy="selectin"
    )


class FoodNutritionEntry(Base):
    __tablename__ = "food_nutrition_table"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("foods.id"), nullable=False)
    nutrition_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("nutrition_table.id"), nullable=False
    )
    value: Mapped[str] = mapped_column(String, nullable=False)
    value_unit: Mapped[str] = mapped_column(String, nullable=False)
    reference_type: Mapped[str] = mapped_column(String, nullable=False)
    reference_unit: Mapped[str] = mapped_column(String, nullable=False)

    food: Mapped[Food] = relationship(back_populates="food_nutrition_entries")
    nutrition: Mapped[NutritionTable] = relationship(back_populates="food_nutrition_entries")


class AnalysisDetail(Base):
    __tablename__ = "analysis_details"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("foods.id"))
    ingredient_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("ingredients.id"))
    analysis_type: Mapped[str] = mapped_column(String, nullable=False)
    results: Mapped[Any | None] = mapped_column(JSONB)
    level: Mapped[str] = mapped_column(String, nullable=False, default="unknown")

    food: Mapped[Food | None] = relationship(back_populates="analysis_details")
    ingredient: Mapped[Ingredient | None] = relationship(back_populates="analysis_details")
