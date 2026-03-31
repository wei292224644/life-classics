from __future__ import annotations

from typing import Literal
from typing_extensions import TypedDict
from pydantic import BaseModel

from workflow_product_analysis.types import (
    RiskLevel, IngredientInput, DemographicItem, ScenarioItem
)


class ProductAnalysisState(TypedDict):
    # ── 输入 ──────────────────────────────────────────────────────────────
    ingredients: list[IngredientInput]

    # ── 中间产物 ───────────────────────────────────────────────────────────
    demographics: list[DemographicItem] | None   # Node A 输出
    scenarios: list[ScenarioItem] | None          # Node B 输出

    # ── 最终产物 ───────────────────────────────────────────────────────────
    advice: str | None                            # Node C 输出
    verdict_level: RiskLevel | None               # Node D 输出
    verdict_description: str | None               # Node D 输出
    references: list[str] | None                  # Node D 输出（过滤后）


# ── Instructor Pydantic 输出模型 ───────────────────────────────────────────

class _DemographicItemModel(BaseModel):
    group: Literal["普通成人", "婴幼儿", "孕妇", "中老年", "运动人群"]
    level: RiskLevel
    note: str

class DemographicsOutput(BaseModel):
    demographics: list[_DemographicItemModel]  # 固定 5 条

class _ScenarioItemModel(BaseModel):
    title: str
    text: str

class ScenariosOutput(BaseModel):
    scenarios: list[_ScenarioItemModel]  # 1-3 条

class AdviceOutput(BaseModel):
    advice: str  # 1-3 句综合建议

class VerdictOutput(BaseModel):
    level: RiskLevel
    description: str
    references: list[str]  # 引用标准，仅引用真实存在的食品安全标准
