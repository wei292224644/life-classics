from __future__ import annotations

from unittest.mock import patch

from langchain_core.exceptions import OutputParserException

from app.core.parser_workflow.nodes.classify_node import _call_classify_llm


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeStructuredChat:
    def __init__(self, invoke_result):
        self._invoke_result = invoke_result

    def invoke(self, _prompt):
        return self._invoke_result


class _FakeChat:
    def __init__(self, invoke_result):
        self._invoke_result = invoke_result

    def with_structured_output(self, _schema, include_raw=False):
        assert include_raw is True
        return _FakeStructuredChat(self._invoke_result)


def test_call_classify_llm_fallback_to_raw_json_when_parser_failed():
    """当结构化解析失败但 raw.content 含 ```json 时，应自动清洗并成功解析。"""
    invoke_result = {
        "raw": _FakeMessage(
            "```json\n"
            '{"segments":[{"content":"前言内容","content_type":"preface","confidence":0.93}]}\n'
            "```"
        ),
        "parsed": None,
        "parsing_error": OutputParserException("Invalid json output: ```json"),
    }
    content_types = [{"id": "preface", "description": "前言"}]

    with patch(
        "app.core.parser_workflow.nodes.classify_node.create_chat_model",
        return_value=_FakeChat(invoke_result),
    ):
        segments = _call_classify_llm("前言", content_types)

    assert len(segments) == 1
    assert segments[0].content == "前言内容"
    assert segments[0].content_type == "preface"
    assert segments[0].confidence == 0.93
