from __future__ import annotations

from typing import Any, Literal, TypedDict

# ── 风险等级 ────────────────────────────────────────────────────────────────
RiskLevel = Literal["t0", "t1", "t2", "t3", "t4"]
IngredientRiskLevel = Literal["t0", "t1", "t2", "t3", "t4", "unknown"]

# ── 任务状态与错误码 ─────────────────────────────────────────────────────────
AnalysisStatus = Literal["ocr", "parsing", "analyzing", "done", "failed"]
AnalysisError = Literal[
    "ocr_failed", "no_ingredients_found", "invalid_food_id", "analysis_failed"
]

# ── 成分匹配 ─────────────────────────────────────────────────────────────────

class MatchedIngredient(TypedDict):
    ingredient_id: int
    name: str
    level: IngredientRiskLevel


class MatchResult(TypedDict):
    matched: list[MatchedIngredient]
    unmatched: list[str]  # 未匹配的原始成分名


# ── Agent 输入 ───────────────────────────────────────────────────────────────

class IngredientInput(TypedDict):
    ingredient_id: int  # unmatched 成分为 0
    name: str
    category: str  # function_type 拼接，如 "增稠剂 · 高升糖指数"
    level: IngredientRiskLevel
    safety_info: str  # 来自 IngredientAnalysis；unknown 成分为空字符串


# ── 结果页条目 ───────────────────────────────────────────────────────────────

class IngredientItem(TypedDict):
    ingredient_id: int
    name: str
    category: str
    level: IngredientRiskLevel


class AlternativeItem(TypedDict):
    current_ingredient_id: int
    better_ingredient_id: int
    reason: str


class DemographicItem(TypedDict):
    group: str  # 普通成人 | 婴幼儿 | 孕妇 | 中老年 | 运动人群
    level: RiskLevel
    note: str


class ScenarioItem(TypedDict):
    title: str
    text: str


# ── 最终产品分析结果 ──────────────────────────────────────────────────────────

class ProductAnalysisResult(TypedDict):
    source: Literal["db_cache", "agent_generated"]
    ingredients: list[IngredientItem]
    verdict: dict[str, Any]  # {level: RiskLevel, description: str}
    advice: str
    alternatives: list[AlternativeItem]
    demographics: list[DemographicItem]
    scenarios: list[ScenarioItem]
    references: list[str]


# ── Redis 任务结构 ────────────────────────────────────────────────────────────

class AnalysisTask(TypedDict):
    task_id: str
    status: AnalysisStatus
    error: AnalysisError | None
    result: ProductAnalysisResult | None
    created_at: str  # ISO 8601
    image_object_key: str | None
