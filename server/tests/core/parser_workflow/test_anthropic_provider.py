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
from parser.structured_llm.errors import StructuredOutputError


class _DummyOutput(BaseModel):
    label: str
    score: float


def _make_streaming_tool_use_response(data: dict) -> MagicMock:
    """构造 anthropic streaming 消息 create 上下文管理器，yield ContentBlockDeltaEvent + InputJSONDelta。"""
    import json

    class _MockInputJSONDelta:
        def __init__(self, partial_json: str):
            self.partial_json = partial_json

    class _MockContentBlockDeltaEvent:
        def __init__(self, partial_json: str):
            self.type = "content_block_delta"
            self.delta = _MockInputJSONDelta(partial_json)

    class _MockMessageStopEvent:
        def __init__(self):
            self.type = "message_stop"

    class _MockStream:
        def __init__(self, data: dict):
            self._json_str = json.dumps(data)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            # 把 JSON 字符串拆成多个 InputJSONDelta chunk
            json_str = self._json_str
            chunk_size = 10
            for i in range(0, len(json_str), chunk_size):
                yield _MockContentBlockDeltaEvent(json_str[i : i + chunk_size])
            yield _MockMessageStopEvent()

    mock_client_instance = MagicMock()
    mock_client_instance.messages.create.return_value = _MockStream(data)
    return mock_client_instance


def test_anthropic_client_calls_messages_create():
    """get_structured_client('anthropic') 返回 callable，调用时走 streaming messages.create。"""
    mock_client_instance = _make_streaming_tool_use_response({"label": "foo", "score": 0.9})

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
    assert call_kwargs["stream"] is True


def _make_streaming_text_only_response() -> MagicMock:
    """构造只返回 text block 的 streaming 响应（无 tool_use/InputJSONDelta）。"""

    class _MockTextDelta:
        def __init__(self):
            self.text = ""

    class _MockContentBlockDeltaEvent:
        def __init__(self):
            self.type = "content_block_delta"
            self.delta = _MockTextDelta()

    class _MockMessageStopEvent:
        def __init__(self):
            self.type = "message_stop"

    class _MockStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            yield _MockContentBlockDeltaEvent()
            yield _MockMessageStopEvent()

    mock_client_instance = MagicMock()
    mock_client_instance.messages.create.return_value = _MockStream()
    return mock_client_instance


def test_anthropic_client_raises_when_no_tool_use_block():
    """响应中无 tool_use block 时抛 ValueError。"""
    mock_client_instance = _make_streaming_text_only_response()

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


from parser.structured_llm import invoke_structured


def test_invoke_structured_anthropic_timeout_retries():
    """anthropic.APITimeoutError 可重试，达到上限后抛 StructuredOutputError。"""
    import anthropic as anthropic_sdk

    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise anthropic_sdk.APITimeoutError(request=MagicMock())

    with patch(
        "parser.structured_llm.invoker.get_structured_client",
        return_value=_fake_create,
    ):
        with pytest.raises(StructuredOutputError) as exc_info:
            invoke_structured(
                node_name="classify_node",
                prompt="test",
                response_model=_DummyOutput,
                provider="anthropic",
                model="MiniMax-Text-01",
                max_retries=2,
            )
        assert exc_info.value.retry_count == 3

    assert call_count == 3


def test_invoke_structured_anthropic_internal_server_error_retries():
    """anthropic.InternalServerError（500）可重试。"""
    import anthropic as anthropic_sdk

    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise anthropic_sdk.InternalServerError(
            message="internal error",
            response=MagicMock(status_code=500),
            body={},
        )

    with patch(
        "parser.structured_llm.invoker.get_structured_client",
        return_value=_fake_create,
    ):
        with pytest.raises(StructuredOutputError):
            invoke_structured(
                node_name="classify_node",
                prompt="test",
                response_model=_DummyOutput,
                provider="anthropic",
                model="MiniMax-Text-01",
                max_retries=1,
            )

    assert call_count == 2


def test_invoke_structured_anthropic_auth_error_no_retry():
    """anthropic.AuthenticationError 不可重试，直接抛出。"""
    import anthropic as anthropic_sdk

    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise anthropic_sdk.AuthenticationError(
            message="invalid api key",
            response=MagicMock(status_code=401),
            body={},
        )

    with patch(
        "parser.structured_llm.invoker.get_structured_client",
        return_value=_fake_create,
    ):
        with pytest.raises(anthropic_sdk.AuthenticationError):
            invoke_structured(
                node_name="classify_node",
                prompt="test",
                response_model=_DummyOutput,
                provider="anthropic",
                model="MiniMax-Text-01",
                max_retries=2,
            )

    assert call_count == 1  # 不重试


def test_get_structured_client_unknown_provider_raises():
    """未知 provider 抛 ValueError，提示包含 anthropic。"""
    from parser.structured_llm.client_factory import get_structured_client
    with pytest.raises(ValueError) as exc_info:
        get_structured_client("unknown_provider", "some-model")
    assert "anthropic" in str(exc_info.value)
