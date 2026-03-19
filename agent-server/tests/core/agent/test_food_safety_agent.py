"""
FoodSafetyAgent 单元测试：验证 agent 创建和基本属性（mock Agno）。
不调用真实 DashScope API。
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.agent.food_safety_agent import create_food_safety_agent


@patch("app.core.agent.food_safety_agent.Agent")
@patch("app.core.agent.food_safety_agent.load_skills", return_value="mocked instructions")
def test_create_food_safety_agent_returns_agent(mock_load_skills, mock_agent_class):
    """create_food_safety_agent 应调用 load_skills 并创建 Agno Agent"""
    mock_agent_instance = MagicMock()
    mock_agent_class.return_value = mock_agent_instance

    agent = create_food_safety_agent()

    mock_load_skills.assert_called_once()
    mock_agent_class.assert_called_once()
    assert agent is mock_agent_instance


@patch("app.core.agent.food_safety_agent.Agent")
@patch("app.core.agent.food_safety_agent.load_skills", return_value="mocked instructions")
def test_create_food_safety_agent_uses_correct_instructions(mock_load_skills, mock_agent_class):
    """Agent 应使用 load_skills 返回的内容作为 instructions"""
    mock_agent_class.return_value = MagicMock()

    create_food_safety_agent()

    call_kwargs = mock_agent_class.call_args[1]
    assert call_kwargs.get("instructions") == "mocked instructions"


@patch("app.core.agent.food_safety_agent.Agent")
@patch("app.core.agent.food_safety_agent.load_skills", return_value="")
def test_create_food_safety_agent_registers_two_tools(mock_load_skills, mock_agent_class):
    """Agent 应注册 knowledge_base 和 web_search 两个工具"""
    mock_agent_class.return_value = MagicMock()

    create_food_safety_agent()

    call_kwargs = mock_agent_class.call_args[1]
    tools = call_kwargs.get("tools", [])
    assert len(tools) == 2
