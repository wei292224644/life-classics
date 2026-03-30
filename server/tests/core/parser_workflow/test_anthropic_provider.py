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
from parser.structured_llm.errors import JsonOutputParseError


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
    """get_structured_client('anthropic') 返回 callable，调用时走 streaming messages.create，使用 JSON system prompt 模式。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert isinstance(result, _DummyOutput)
    assert result.label == "foo"
    assert result.score == 0.9
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    assert call_kwargs["stream"] is True
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


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


def _make_streaming_text_response(text: str) -> MagicMock:
    """构造返回指定文本内容的 TextDelta streaming 响应。"""

    class _MockTextDelta:
        def __init__(self, content: str):
            self.text = content

    class _MockContentBlockDeltaEvent:
        def __init__(self, content: str):
            self.type = "content_block_delta"
            self.delta = _MockTextDelta(content)

    class _MockMessageStopEvent:
        def __init__(self):
            self.type = "message_stop"

    class _MockStream:
        def __init__(self, content: str):
            self._content = content

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            yield _MockContentBlockDeltaEvent(self._content)
            yield _MockMessageStopEvent()

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _MockStream(text)
    return mock_client


def test_anthropic_client_raises_when_no_parseable_json():
    """响应中无可解析的 JSON 时抛 JsonOutputParseError。"""
    mock_client = _make_streaming_text_response("这是普通文本，完全没有 JSON")

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        with pytest.raises(JsonOutputParseError):
            create_fn(
                model="MiniMax-M2.7",
                messages=[{"role": "user", "content": "test"}],
                response_model=_DummyOutput,
            )


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


def test_json_output_parse_error_is_importable_and_is_runtime_error():
    """JsonOutputParseError 可从 errors 模块导入，且是 RuntimeError 子类。"""
    from parser.structured_llm.errors import JsonOutputParseError
    err = JsonOutputParseError("test message")
    assert isinstance(err, RuntimeError)
    assert "test message" in str(err)


def test_json_mode_no_tools_in_request():
    """JSON system prompt 模式不传 tools / tool_choice 参数。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


def test_json_mode_system_contains_schema():
    """create 调用包含 system 参数，且内容包含 response_model 的字段名。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    assert "label" in call_kwargs["system"]
    assert "score" in call_kwargs["system"]


def test_json_mode_direct_json_response():
    """模型直接返回裸 JSON 时，正确解析为 response_model。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert isinstance(result, _DummyOutput)
    assert result.label == "foo"
    assert result.score == 0.9


def test_json_mode_markdown_block_response():
    """模型返回 ```json ... ``` 包裹时，提取后正确解析。"""
    text = '```json\n{"label": "bar", "score": 0.5}\n```'
    mock_client = _make_streaming_text_response(text)

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert result.label == "bar"
    assert result.score == 0.5


def test_json_mode_json_embedded_in_text():
    """模型返回文字中嵌入 JSON 对象时，提取后正确解析。"""
    text = '好的，结果如下：{"label": "baz", "score": 0.3} 以上是结果。'
    mock_client = _make_streaming_text_response(text)

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        # 新实现应该能提取嵌入文本中的 JSON 并正确解析
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert result.label == "baz"
    assert result.score == 0.3


def test_json_mode_invalid_json_raises_parse_error():
    """模型返回无法解析的文本时，抛 JsonOutputParseError（新实现）。"""
    mock_client = _make_streaming_text_response("这是普通文本，完全没有 JSON 内容")

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        # 新实现应该抛 JsonOutputParseError，而非 ValueError
        with pytest.raises(JsonOutputParseError):
            create_fn(
                model="MiniMax-M2.7",
                messages=[{"role": "user", "content": "test"}],
                response_model=_DummyOutput,
            )


def test_invoke_structured_json_parse_error_retries():
    """JsonOutputParseError 可重试，达上限后抛 StructuredOutputError。"""
    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise JsonOutputParseError("JSON 解析失败")

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
                model="MiniMax-M2.7",
                max_retries=2,
            )
        assert exc_info.value.retry_count == 3

    assert call_count == 3  # 首次 + 2 次重试


def test_invoke_structured_json_parse_error_single_retry():
    """JsonOutputParseError max_retries=0 时不重试，直接抛 StructuredOutputError。"""
    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise JsonOutputParseError("JSON 解析失败")

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
                model="MiniMax-M2.7",
                max_retries=0,
            )

    assert call_count == 1
