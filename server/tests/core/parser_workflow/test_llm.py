# from __future__ import annotations

# import pytest
# from unittest.mock import MagicMock, patch

# from parser.llm import create_chat_model, resolve_provider


# # ── resolve_provider ────────────────────────────────────────────────────────

# def test_resolve_provider_explicit():
#     """明确传入 provider 时直接返回。"""
#     assert resolve_provider("ollama") == "ollama"


# def test_resolve_provider_fallback_to_global():
#     """node_provider 为空时，回退到 PARSER_LLM_PROVIDER。"""
#     mock_settings = MagicMock()
#     mock_settings.PARSER_LLM_PROVIDER = "dashscope"
#     with patch("app.core.parser_workflow.llm.settings", mock_settings):
#         assert resolve_provider("") == "dashscope"
#         assert resolve_provider(None) == "dashscope"


# def test_resolve_provider_hardcoded_fallback():
#     """PARSER_LLM_PROVIDER 也为空时，回退到 'openai'。"""
#     mock_settings = MagicMock()
#     mock_settings.PARSER_LLM_PROVIDER = ""
#     with patch("app.core.parser_workflow.llm.settings", mock_settings):
#         assert resolve_provider(None) == "openai"


# # ── create_chat_model ───────────────────────────────────────────────────────

# def test_create_chat_model_openai():
#     """provider='openai' 返回 ChatOpenAI 实例。"""
#     from langchain_openai import ChatOpenAI
#     with patch("app.core.parser_workflow.llm.settings") as mock_settings:
#         mock_settings.LLM_API_KEY = "test-key"
#         mock_settings.LLM_BASE_URL = ""
#         model = create_chat_model("gpt-4o", "openai")
#     assert isinstance(model, ChatOpenAI)


# def test_create_chat_model_dashscope():
#     """provider='dashscope' 返回 ChatOpenAI 实例，且自动注入 extra_body={"enable_thinking": False}。"""
#     from langchain_openai import ChatOpenAI
#     with patch("app.core.parser_workflow.llm.settings") as mock_settings:
#         mock_settings.DASHSCOPE_API_KEY = "ds-key"
#         mock_settings.DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
#         model = create_chat_model("qwen-max", "dashscope")
#     assert isinstance(model, ChatOpenAI)
#     # 验证 extra_body 已自动注入（langchain_openai 将 extra_body 存为 Pydantic 字段）
#     extra = getattr(model, "extra_body", None) or model.model_kwargs.get("extra_body")
#     assert extra == {"enable_thinking": False}


# def test_create_chat_model_ollama():
#     """provider='ollama' 返回 ChatOllama 实例，且默认关闭 thinking(reasoning) 模式。"""
#     from langchain_ollama import ChatOllama
#     with patch("app.core.parser_workflow.llm.settings") as mock_settings:
#         mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
#         model = create_chat_model("llama3", "ollama")
#     assert isinstance(model, ChatOllama)
#     assert model.reasoning is False


# def test_create_chat_model_unknown_provider():
#     """未知 provider 抛出 ValueError，错误信息包含 provider 名。"""
#     with pytest.raises(ValueError, match="unknown_xyz"):
#         create_chat_model("some-model", "unknown_xyz")
