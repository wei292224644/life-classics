import pytest
from unittest.mock import patch

from app.core.parser_workflow.models import RawChunk, WorkflowState
from app.core.parser_workflow.nodes.classify_node import (
    classify_node,
    classify_raw_chunk,
)


def _raw(content: str) -> RawChunk:
    return RawChunk(content=content, section_path=["3 范围"], char_count=len(content))


def _make_state(chunks: list, rules_dir: str = "/tmp", config: dict | None = None) -> WorkflowState:
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "GB_TEST", "title": "t"},
        config=config
        or {
            "classify_model": "gpt-mock",
            "llm_api_key": "test",
        },
        rules_dir=rules_dir,
        raw_chunks=chunks,
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


MOCK_LLM_RESPONSE = {
    "segments": [
        {"content": "普通文本内容", "content_type": "plain_text", "confidence": 0.95},
    ],
}


def test_classify_marks_all_confident_segments(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=MOCK_LLM_RESPONSE,
    ):
        state = _make_state([_raw("普通文本内容")], rules_dir=str(tmp_path))
        result = classify_node(state)
    assert len(result["classified_chunks"]) == 1
    cc = result["classified_chunks"][0]
    assert cc["has_unknown"] is False
    assert cc["segments"][0]["content_type"] == "plain_text"
    assert cc["segments"][0]["escalated"] is False


def test_classify_marks_low_confidence_as_unknown(tmp_path):
    low_conf_response = {
        "segments": [
            {"content": "奇怪内容", "content_type": "plain_text", "confidence": 0.3},
        ],
    }
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=low_conf_response,
    ):
        state = _make_state(
            [_raw("奇怪内容")],
            rules_dir=str(tmp_path),
            config={
                "classify_model": "m",
                "llm_api_key": "k",
                "confidence_threshold": 0.7,
            },
        )
        result = classify_node(state)
    assert result["classified_chunks"][0]["has_unknown"] is True
    assert result["classified_chunks"][0]["segments"][0]["content_type"] == "unknown"


def test_classify_mixed_chunk_partial_unknown(tmp_path):
    mixed_low = {
        "segments": [
            {"content": "正常内容", "content_type": "plain_text", "confidence": 0.95},
            {"content": "奇怪片段", "content_type": "plain_text", "confidence": 0.2},
        ],
    }
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=mixed_low,
    ):
        state = _make_state(
            [_raw("正常内容\n奇怪片段")],
            rules_dir=str(tmp_path),
        )
        result = classify_node(state)
    cc = result["classified_chunks"][0]
    assert cc["has_unknown"] is True
    unknowns = [s for s in cc["segments"] if s["content_type"] == "unknown"]
    assert len(unknowns) == 1


def test_classify_fills_transform_params_from_rules(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=MOCK_LLM_RESPONSE,
    ):
        state = _make_state([_raw("普通文本内容")], rules_dir=str(tmp_path))
        result = classify_node(state)
    seg = result["classified_chunks"][0]["segments"][0]
    assert "strategy" in seg["transform_params"]


def test_classify_multiple_chunks_all_classified(tmp_path):
    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=MOCK_LLM_RESPONSE,
    ):
        state = _make_state(
            [_raw("内容A"), _raw("内容B")],
            rules_dir=str(tmp_path),
        )
        result = classify_node(state)
    assert len(result["classified_chunks"]) == 2

