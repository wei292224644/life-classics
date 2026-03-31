# """structured_llm 模块单元测试。"""

# from __future__ import annotations

# from unittest.mock import MagicMock, patch

# import pytest
# from pydantic import BaseModel
# from pydantic import ValidationError as PydanticValidationError

# from api.config import Settings, settings
# from worflow_parser_kb.structured_llm import (
#     StructuredOutputError,
#     invoke_structured,
#     resolve_model_for_node,
#     resolve_provider_for_node,
# )
# from worflow_parser_kb.structured_llm.client_factory import get_structured_client


# # ── 配置默认值 ────────────────────────────────────────────────────────────────


# def test_structured_settings_defaults():
#     """新增配置项默认值正确。"""
#     s = Settings()
#     assert s.PARSER_STRUCTURED_MAX_RETRIES == 2
#     assert s.PARSER_STRUCTURED_TIMEOUT_SECONDS == 60
#     assert s.PARSER_STRUCTURED_TEMPERATURE == 0.0
#     assert s.PARSER_STRUCTURED_LOG_PROMPT_PREVIEW is False


# # ── resolve_model_for_node ────────────────────────────────────────────────────


# def test_resolve_model_for_transform_fallback():
#     """transform_node 且 node_model 为空时返回 fallback_model。"""
#     model = resolve_model_for_node(
#         node_name="transform_node",
#         node_model="",
#         fallback_model="qwen-max",
#     )
#     assert model == "qwen-max"


# def test_resolve_model_for_transform_with_model():
#     """transform_node 且 node_model 非空时返回 node_model。"""
#     model = resolve_model_for_node(
#         node_name="transform_node",
#         node_model="qwen-turbo",
#         fallback_model="qwen-max",
#     )
#     assert model == "qwen-turbo"


# def test_resolve_model_for_classify():
#     """classify_node 返回 node_model。"""
#     model = resolve_model_for_node(
#         node_name="classify_node",
#         node_model="qwen-turbo",
#         fallback_model="",
#     )
#     assert model == "qwen-turbo"


# def test_resolve_model_for_other_node():
#     """非 transform 节点不触发 fallback。"""
#     model = resolve_model_for_node(
#         node_name="escalate_node",
#         node_model="",
#         fallback_model="qwen-max",
#     )
#     assert model == ""


# # ── resolve_provider_for_node ──────────────────────────────────────────────────


# def test_resolve_provider_for_node_priority_node():
#     """优先使用 node_provider。"""
#     assert resolve_provider_for_node("dashscope", "openai") == "dashscope"


# def test_resolve_provider_for_node_priority_global():
#     """node_provider 为空时使用 global_provider。"""
#     assert resolve_provider_for_node("", "dashscope") == "dashscope"
#     assert resolve_provider_for_node(None, "ollama") == "ollama"


# def test_resolve_provider_for_node_hardcoded_fallback():
#     """两者都为空时回退到 openai。"""
#     assert resolve_provider_for_node("", "") == "openai"
#     assert resolve_provider_for_node(None, None) == "openai"


# # ── StructuredOutputError 字段 ────────────────────────────────────────────────


# def test_structured_output_error_fields():
#     """StructuredOutputError 各属性可访问。"""
#     err = StructuredOutputError(
#         "test message",
#         provider="openai",
#         model="gpt-4",
#         node_name="classify_node",
#         response_model="ClassifyOutput",
#         retry_count=2,
#         raw_error="ValidationError: ...",
#     )
#     assert err.provider == "openai"
#     assert err.model == "gpt-4"
#     assert err.node_name == "classify_node"
#     assert err.response_model == "ClassifyOutput"
#     assert err.retry_count == 2
#     assert err.raw_error == "ValidationError: ..."
#     assert "test message" in str(err)


# # ── invoke_structured 行为 ───────────────────────────────────────────────────


# class _DummyOutput(BaseModel):
#     content: str


# def test_invoke_structured_validation_error_no_retry():
#     """Pydantic ValidationError 不重试，直接抛 StructuredOutputError。"""
#     call_count = 0

#     def _fake_create(*, model, messages, response_model, **kwargs):
#         nonlocal call_count
#         call_count += 1
#         try:
#             response_model.model_validate({})
#         except PydanticValidationError as e:
#             raise e

#     with patch(
#         "app.core.parser_workflow.structured_llm.invoker.get_structured_client",
#         return_value=_fake_create,
#     ):
#         with pytest.raises(StructuredOutputError) as exc_info:
#             invoke_structured(
#                 node_name="classify_node",
#                 prompt="test",
#                 response_model=_DummyOutput,
#                 provider="openai",
#                 model="gpt-4",
#             )
#         assert exc_info.value.retry_count == 0
#         assert "DummyOutput" in exc_info.value.response_model
#     assert call_count == 1


# def test_invoke_structured_timeout_error_retries_until_max():
#     """TimeoutError 会重试到上限。"""
#     call_count = 0

#     def _fake_create(*, model, messages, response_model, **kwargs):
#         nonlocal call_count
#         call_count += 1
#         raise TimeoutError("connection timed out")

#     with patch(
#         "app.core.parser_workflow.structured_llm.invoker.get_structured_client",
#         return_value=_fake_create,
#     ):
#         with pytest.raises(StructuredOutputError) as exc_info:
#             invoke_structured(
#                 node_name="classify_node",
#                 prompt="test",
#                 response_model=_DummyOutput,
#                 provider="openai",
#                 model="gpt-4",
#                 max_retries=2,
#             )
#         assert exc_info.value.retry_count == 3  # 初始 1 次 + 重试 2 次
#     assert call_count == 3


# def test_invoke_structured_connection_error_retries_until_max():
#     """ConnectionError 会重试到上限。"""
#     call_count = 0

#     def _fake_create(*, model, messages, response_model, **kwargs):
#         nonlocal call_count
#         call_count += 1
#         raise ConnectionError("connection refused")

#     with patch(
#         "app.core.parser_workflow.structured_llm.invoker.get_structured_client",
#         return_value=_fake_create,
#     ):
#         with pytest.raises(StructuredOutputError) as exc_info:
#             invoke_structured(
#                 node_name="classify_node",
#                 prompt="test",
#                 response_model=_DummyOutput,
#                 provider="openai",
#                 model="gpt-4",
#                 max_retries=2,
#             )
#         assert exc_info.value.retry_count == 3
#     assert call_count == 3


# def test_invoke_structured_success_returns_model():
#     """成功时返回 response_model 实例。"""
#     def _fake_create(*, model, messages, response_model, **kwargs):
#         return response_model(content="hello")

#     with patch(
#         "app.core.parser_workflow.structured_llm.invoker.get_structured_client",
#         return_value=_fake_create,
#     ):
#         result = invoke_structured(
#             node_name="classify_node",
#             prompt="test",
#             response_model=_DummyOutput,
#             provider="openai",
#             model="gpt-4",
#         )
#     assert isinstance(result, _DummyOutput)
#     assert result.content == "hello"


# # ── invoke_structured 从 settings 解析 provider/model ────────────────────────


# def test_invoke_structured_resolves_provider_model_from_settings():
#     """provider/model 为空时从 settings 按 node_name 解析。"""
#     captured = {}

#     def _fake_create(*, model, messages, response_model, **kwargs):
#         captured["model"] = model
#         captured["provider"] = "from_closure"  # 无法直接拿到，通过下面 assert model 推断
#         return response_model(content="ok")

#     with patch(
#         "app.core.parser_workflow.structured_llm.invoker.get_structured_client",
#         return_value=_fake_create,
#     ), patch.object(settings, "CLASSIFY_MODEL", "qwen-turbo"), patch.object(
#         settings, "CLASSIFY_LLM_PROVIDER", ""
#     ), patch.object(settings, "PARSER_LLM_PROVIDER", "openai"):
#         result = invoke_structured(
#             node_name="classify_node",
#             prompt="test",
#             response_model=_DummyOutput,
#             provider=None,
#             model=None,
#         )
#     assert result.content == "ok"
#     assert captured["model"] == "qwen-turbo"


# def test_invoke_structured_classify_node_empty_model_raises():
#     """classify_node model 为空时抛 ValueError。"""
#     with patch.object(settings, "CLASSIFY_MODEL", ""), patch.object(
#         settings, "CLASSIFY_LLM_PROVIDER", ""
#     ), patch.object(settings, "PARSER_LLM_PROVIDER", "openai"):
#         with pytest.raises(ValueError, match="model 为空"):
#             invoke_structured(
#                 node_name="classify_node",
#                 prompt="test",
#                 response_model=_DummyOutput,
#                 provider=None,
#                 model=None,
#             )


# def test_invoke_structured_transform_node_empty_model_fallbacks_to_escalate():
#     """transform_node model 为空时 fallback 到 ESCALATE_MODEL。"""
#     captured = {}

#     def _fake_create(*, model, messages, response_model, **kwargs):
#         captured["model"] = model
#         return response_model(content="ok")

#     with patch(
#         "app.core.parser_workflow.structured_llm.invoker.get_structured_client",
#         return_value=_fake_create,
#     ), patch.object(settings, "TRANSFORM_MODEL", ""), patch.object(
#         settings, "ESCALATE_MODEL", "qwen-max"
#     ), patch.object(settings, "TRANSFORM_LLM_PROVIDER", ""), patch.object(
#         settings, "PARSER_LLM_PROVIDER", "openai"
#     ):
#         result = invoke_structured(
#             node_name="transform_node",
#             prompt="test",
#             response_model=_DummyOutput,
#             provider=None,
#             model=None,
#         )
#     assert result.content == "ok"
#     assert captured["model"] == "qwen-max"


# # ── client_factory provider 参数注入 ──────────────────────────────────────────


# def test_client_factory_dashscope_injects_enable_thinking():
#     """dashscope 分支注入 enable_thinking=False。"""
#     mock_client = MagicMock()
#     mock_client.chat.completions.create.return_value = _DummyOutput(content="x")

#     with patch(
#         "app.core.parser_workflow.structured_llm.client_factory._create_openai_client",
#         return_value=mock_client,
#     ):
#         create_fn = get_structured_client("dashscope")
#         create_fn(
#             model="qwen-max",
#             messages=[{"role": "user", "content": "hi"}],
#             response_model=_DummyOutput,
#         )
#     mock_client.chat.completions.create.assert_called_once()
#     call_kwargs = mock_client.chat.completions.create.call_args.kwargs
#     assert call_kwargs["extra_body"] == {"enable_thinking": False}


# def test_client_factory_ollama_does_not_inject_reasoning_by_default():
#     """ollama 分支默认不注入 reasoning（避免 OpenAI-compatible 400）。"""
#     mock_client = MagicMock()
#     mock_client.chat.completions.create.return_value = _DummyOutput(content="x")

#     with patch(
#         "app.core.parser_workflow.structured_llm.client_factory._create_openai_client",
#         return_value=mock_client,
#     ):
#         create_fn = get_structured_client("ollama")
#         create_fn(
#             model="llama3",
#             messages=[{"role": "user", "content": "hi"}],
#             response_model=_DummyOutput,
#         )
#     mock_client.chat.completions.create.assert_called_once()
#     call_kwargs = mock_client.chat.completions.create.call_args.kwargs
#     assert "extra_body" not in call_kwargs
