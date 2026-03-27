"""测试 SearchRepository 的 DB 查询逻辑（mock session）。"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db_repositories.search import SearchRepository


@pytest.mark.asyncio
async def test_search_foods_empty_when_no_match():
    """名称无匹配时应直接返回空列表，只执行一次 execute。"""
    mock_session = AsyncMock()
    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock_session.execute.return_value = empty_result

    repo = SearchRepository(mock_session)
    result = await repo.search_foods("不存在的食品")

    assert result == []
    assert mock_session.execute.call_count == 1


@pytest.mark.asyncio
async def test_search_foods_maps_risk_and_high_risk_count():
    """有匹配时应正确映射 risk_level 和 high_risk_count。"""
    mock_session = AsyncMock()

    foods_result = MagicMock()
    foods_result.all.return_value = [
        SimpleNamespace(id=1, barcode="6901234", name="测试饼干", product_category="零食")
    ]
    risk_result = MagicMock()
    risk_result.all.return_value = [
        SimpleNamespace(target_id=1, level="t2")
    ]
    high_risk_result = MagicMock()
    high_risk_result.all.return_value = [
        SimpleNamespace(food_id=1, cnt=2)
    ]

    mock_session.execute.side_effect = [foods_result, risk_result, high_risk_result]

    repo = SearchRepository(mock_session)
    result = await repo.search_foods("饼干")

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].barcode == "6901234"
    assert result[0].name == "测试饼干"
    assert result[0].product_category == "零食"
    assert result[0].risk_level == "t2"
    assert result[0].high_risk_count == 2


@pytest.mark.asyncio
async def test_search_foods_defaults_unknown_when_no_analysis():
    """食品无 overall_risk 分析时 risk_level 应为 unknown，high_risk_count 为 0。"""
    mock_session = AsyncMock()

    foods_result = MagicMock()
    foods_result.all.return_value = [
        SimpleNamespace(id=5, barcode="999", name="无分析食品", product_category=None)
    ]
    risk_result = MagicMock()
    risk_result.all.return_value = []  # 无分析
    high_risk_result = MagicMock()
    high_risk_result.all.return_value = []  # 无高风险配料

    mock_session.execute.side_effect = [foods_result, risk_result, high_risk_result]

    repo = SearchRepository(mock_session)
    result = await repo.search_foods("无分析")

    assert result[0].risk_level == "unknown"
    assert result[0].high_risk_count == 0


@pytest.mark.asyncio
async def test_search_ingredients_empty_when_no_match():
    """配料无匹配时直接返回空列表。"""
    mock_session = AsyncMock()
    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock_session.execute.return_value = empty_result

    repo = SearchRepository(mock_session)
    result = await repo.search_ingredients("不存在")

    assert result == []
    assert mock_session.execute.call_count == 1


@pytest.mark.asyncio
async def test_search_ingredients_maps_risk_level():
    """有匹配时应正确映射 risk_level。"""
    mock_session = AsyncMock()

    ings_result = MagicMock()
    ings_result.all.return_value = [
        SimpleNamespace(id=10, name="苯甲酸钠", function_type=["防腐剂"])
    ]
    risk_result = MagicMock()
    risk_result.all.return_value = [
        SimpleNamespace(target_id=10, level="t4")
    ]

    mock_session.execute.side_effect = [ings_result, risk_result]

    repo = SearchRepository(mock_session)
    result = await repo.search_ingredients("苯甲")

    assert len(result) == 1
    assert result[0].id == 10
    assert result[0].name == "苯甲酸钠"
    assert result[0].function_type == ["防腐剂"]
    assert result[0].risk_level == "t4"
