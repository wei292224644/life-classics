"""Tests for product analysis agent nodes."""
from __future__ import annotations

import pytest

from workflow_product_analysis.product_agent.types import (
    DemographicsOutput,
    ScenariosOutput,
    AdviceOutput,
    VerdictOutput,
)


SAMPLE_INGREDIENTS = [
    {"ingredient_id": 1, "name": "燕麦粉", "category": "主原料", "level": "t0", "safety_info": "安全"},
    {"ingredient_id": 2, "name": "阿斯巴甜", "category": "甜味剂", "level": "t2", "safety_info": "适量使用"},
]

SAMPLE_STATE = {
    "ingredients": SAMPLE_INGREDIENTS,
    "demographics": None,
    "scenarios": None,
    "advice": None,
    "verdict_level": None,
    "verdict_description": None,
    "references": None,
}


@pytest.mark.asyncio
async def test_demographics_output_model():
    """DemographicsOutput Pydantic model validates correctly."""
    output = DemographicsOutput(demographics=[])
    assert output.demographics == []

    from workflow_product_analysis.product_agent.types import _DemographicItemModel
    item = _DemographicItemModel(group="普通成人", level="t1", note="适量食用")
    assert item.group == "普通成人"
    assert item.level == "t1"


@pytest.mark.asyncio
async def test_scenarios_output_model():
    """ScenariosOutput Pydantic model validates correctly."""
    output = ScenariosOutput(scenarios=[
        {"title": "上午加餐", "text": "可以搭配牛奶"}
    ])
    assert len(output.scenarios) == 1
    assert output.scenarios[0].title == "上午加餐"


@pytest.mark.asyncio
async def test_advice_output_model():
    """AdviceOutput Pydantic model validates correctly."""
    output = AdviceOutput(advice="适合普通人食用")
    assert output.advice == "适合普通人食用"


@pytest.mark.asyncio
async def test_verdict_output_model():
    """VerdictOutput Pydantic model validates correctly."""
    output = VerdictOutput(
        level="t1",
        description="适量食用",
        references=["GB 2760", "GB 7718"],
    )
    assert output.level == "t1"
    assert output.description == "适量食用"
    assert len(output.references) == 2


@pytest.mark.asyncio
async def test_product_analysis_state_structure():
    """ProductAnalysisState TypedDict accepts all required fields."""
    from workflow_product_analysis.product_agent.types import ProductAnalysisState

    state = ProductAnalysisState(
        ingredients=SAMPLE_INGREDIENTS,
        demographics=[{"group": "普通成人", "level": "t1", "note": "ok"}],
        scenarios=[{"title": "上午", "text": "可食用"}],
        advice="test advice",
        verdict_level="t1",
        verdict_description="安全",
        references=["GB 2760"],
    )
    assert state["ingredients"] == SAMPLE_INGREDIENTS
    assert state["demographics"][0]["group"] == "普通成人"
    assert state["scenarios"][0]["title"] == "上午"
