import pytest
from unittest.mock import MagicMock, patch

from workflow_product_analysis.product_agent.types import (
    DemographicsOutput, _DemographicItemModel,
    ScenariosOutput, _ScenarioItemModel,
    AdviceOutput, VerdictOutput,
)
from workflow_product_analysis.product_agent.nodes import (
    demographics_node, scenarios_node, advice_node, verdict_node,
)


class MockSettings:
    PARSER_LLM_PROVIDER = "anthropic"
    ANALYSIS_DEMOGRAPHICS_MODEL = "qwen-plus"
    ANALYSIS_SCENARIOS_MODEL = "qwen-plus"
    ANALYSIS_ADVICE_MODEL = "qwen-plus"
    ANALYSIS_VERDICT_MODEL = "qwen-max"
    ANALYSIS_REFERENCES_ALLOWLIST = "GB 2760,GB 7718,GB 28050"
    LLM_API_KEY = "test"
    LLM_BASE_URL = "http://localhost"


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


@pytest.fixture
def settings():
    return MockSettings()


@pytest.mark.asyncio
async def test_demographics_node_returns_5_items(settings):
    mock_output = DemographicsOutput(demographics=[
        _DemographicItemModel(group="普通成人", level="t1", note="适量食用"),
        _DemographicItemModel(group="婴幼儿", level="t3", note="不建议"),
        _DemographicItemModel(group="孕妇", level="t2", note="注意阿斯巴甜"),
        _DemographicItemModel(group="中老年", level="t1", note="注意血糖"),
        _DemographicItemModel(group="运动人群", level="t0", note="可以食用"),
    ])
    mock_create = MagicMock(return_value=mock_output)
    with patch("workflow_product_analysis.product_agent.nodes.get_structured_client", return_value=mock_create) as mock_factory:
        with patch("workflow_product_analysis.product_agent.nodes.asyncio.to_thread", side_effect=lambda fn, **kw: fn(**kw)):
            result = await demographics_node(SAMPLE_STATE, settings)
            assert len(result["demographics"]) == 5
            assert result["demographics"][0]["group"] == "普通成人"


@pytest.mark.asyncio
async def test_scenarios_node_returns_scenarios(settings):
    mock_output = ScenariosOutput(scenarios=[
        _ScenarioItemModel(title="上午加餐", text="可以在上午搭配牛奶食用"),
    ])
    mock_create = MagicMock(return_value=mock_output)
    with patch("workflow_product_analysis.product_agent.nodes.get_structured_client", return_value=mock_create):
        with patch("workflow_product_analysis.product_agent.nodes.asyncio.to_thread", side_effect=lambda fn, **kw: fn(**kw)):
            result = await scenarios_node(SAMPLE_STATE, settings)
            assert len(result["scenarios"]) == 1
            assert result["scenarios"][0]["title"] == "上午加餐"


@pytest.mark.asyncio
async def test_advice_node_returns_string(settings):
    mock_output = AdviceOutput(advice="总体来看，该产品适合普通成人适量食用。")
    mock_create = MagicMock(return_value=mock_output)
    with patch("workflow_product_analysis.product_agent.nodes.get_structured_client", return_value=mock_create):
        with patch("workflow_product_analysis.product_agent.nodes.asyncio.to_thread", side_effect=lambda fn, **kw: fn(**kw)):
            state = {**SAMPLE_STATE, "demographics": [], "scenarios": []}
            result = await advice_node(state, settings)
            assert "advice" in result
            assert len(result["advice"]) > 0


@pytest.mark.asyncio
async def test_verdict_node_filters_references(settings):
    """未在白名单的引用应被过滤掉。"""
    mock_output = VerdictOutput(
        level="t1",
        description="含有甜味剂，适量食用",
        references=["GB 2760", "GB 9999-FAKE", "GB 7718"],  # 第二条应被过滤
    )
    mock_create = MagicMock(return_value=mock_output)
    with patch("workflow_product_analysis.product_agent.nodes.get_structured_client", return_value=mock_create):
        with patch("workflow_product_analysis.product_agent.nodes.asyncio.to_thread", side_effect=lambda fn, **kw: fn(**kw)):
            state = {**SAMPLE_STATE, "demographics": [], "scenarios": [], "advice": "ok"}
            result = await verdict_node(state, settings)
            assert result["verdict_level"] == "t1"
            assert "GB 2760" in result["references"]
            assert "GB 9999-FAKE" not in result["references"]
            assert "GB 7718" in result["references"]


@pytest.mark.asyncio
async def test_verdict_node_all_filtered_returns_empty(settings):
    """全部 references 被过滤时返回空数组。"""
    mock_output = VerdictOutput(
        level="t0",
        description="很安全",
        references=["FAKE-001", "FAKE-002"],
    )
    mock_create = MagicMock(return_value=mock_output)
    with patch("workflow_product_analysis.product_agent.nodes.get_structured_client", return_value=mock_create):
        with patch("workflow_product_analysis.product_agent.nodes.asyncio.to_thread", side_effect=lambda fn, **kw: fn(**kw)):
            state = {**SAMPLE_STATE, "demographics": [], "scenarios": [], "advice": "ok"}
            result = await verdict_node(state, settings)
            assert result["references"] == []
