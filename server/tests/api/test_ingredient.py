"""测试 IngredientService（通过 mock repository）。"""
import pytest

from db_repositories.ingredient import IngredientDetail
from api.product.service import IngredientService


def _make_detail(analyses: list[dict]) -> IngredientDetail:
    return IngredientDetail(
        id=1,
        name="苯甲酸钠",
        alias=["安息香酸钠"],
        description="一种常见防腐剂",
        is_additive=True,
        additive_code="E211",
        standard_code="GB 2760",
        who_level="2B",
        allergen_info=[],
        function_type=["防腐剂"],
        origin_type="化学合成",
        limit_usage="1g/kg",
        legal_region="中国",
        cas="532-32-1",
        applications="饮料、果酱",
        notes=None,
        safety_info=None,
        analyses=analyses,
        related_products=[],
    )


def test_ingredient_response_analyses_empty():
    """无分析记录时 analyses 为空列表。"""
    svc = IngredientService(None)
    resp = svc._to_ingredient_response(_make_detail([]))
    assert resp.analyses == []


def test_ingredient_response_analyses_multiple():
    """多条分析记录全部映射到 analyses 列表。"""
    svc = IngredientService(None)
    detail = _make_detail([
        {
            "analysis_type": "ingredient_summary",
            "result": "中等风险防腐剂",
            "source": None,
            "level": "t2",
            "confidence_score": 80,
        },
        {
            "analysis_type": "overall_risk",
            "result": "综合评估为中等风险",
            "source": None,
            "level": "t2",
            "confidence_score": 85,
        },
    ])
    resp = svc._to_ingredient_response(detail)
    assert len(resp.analyses) == 2
    types = [a.analysis_type for a in resp.analyses]
    assert "ingredient_summary" in types
    assert "overall_risk" in types


def test_ingredient_response_overall_risk_level():
    """analyses 中可以找到 overall_risk 并读取其 level。"""
    svc = IngredientService(None)
    detail = _make_detail([
        {
            "analysis_type": "overall_risk",
            "result": "综合评估为高风险",
            "source": None,
            "level": "t3",
            "confidence_score": 90,
        },
    ])
    resp = svc._to_ingredient_response(detail)
    overall = next(a for a in resp.analyses if a.analysis_type == "overall_risk")
    assert overall.level.value == "t3"
