"""anthropic provider 单元测试。"""
from __future__ import annotations

from config import Settings


def test_anthropic_config_defaults():
    """ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL 默认为空字符串。"""
    s = Settings()
    assert s.ANTHROPIC_API_KEY == ""
    assert s.ANTHROPIC_BASE_URL == ""


from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from parser.structured_llm.client_factory import get_structured_client


class _DummyOutput(BaseModel):
    label: str
    score: float


def _make_tool_use_response(data: dict) -> MagicMock:
    """构造 anthropic messages.create 返回值，包含一个 tool_use block。"""
    block = MagicMock()
    block.type = "tool_use"
    block.input = data
    response = MagicMock()
    response.content = [block]
    return response


def test_anthropic_client_calls_messages_create():
    """get_structured_client('anthropic') 返回 callable，调用时走 messages.create。"""
    mock_client_instance = MagicMock()
    mock_client_instance.messages.create.return_value = _make_tool_use_response(
        {"label": "foo", "score": 0.9}
    )

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client_instance
        create_fn = get_structured_client("anthropic", "MiniMax-Text-01")
        result = create_fn(
            model="MiniMax-Text-01",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert isinstance(result, _DummyOutput)
    assert result.label == "foo"
    assert result.score == 0.9
    mock_client_instance.messages.create.assert_called_once()
    call_kwargs = mock_client_instance.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "_DummyOutput"}
    assert call_kwargs["tools"][0]["name"] == "_DummyOutput"
    assert "input_schema" in call_kwargs["tools"][0]


def test_anthropic_client_raises_when_no_tool_use_block():
    """响应中无 tool_use block 时抛 ValueError。"""
    mock_client_instance = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    mock_response = MagicMock()
    mock_response.content = [text_block]
    mock_client_instance.messages.create.return_value = mock_response

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client_instance
        create_fn = get_structured_client("anthropic", "MiniMax-Text-01")
        with pytest.raises(ValueError) as exc_info:
            create_fn(
                model="MiniMax-Text-01",
                messages=[{"role": "user", "content": "test"}],
                response_model=_DummyOutput,
            )
    assert "tool_use block" in str(exc_info.value)
