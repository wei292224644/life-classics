import pytest

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.nodes.transform_node import apply_strategy, transform_node


def _seg(content: str, ct: str, strategy: str = "plain_embed") -> TypedSegment:
    return TypedSegment(
        content=content,
        content_type=ct,
        transform_params={"strategy": strategy},
        confidence=0.9,
        escalated=False,
    )


def _raw(content: str) -> RawChunk:
    return RawChunk(content=content, section_path=["3 范围"], char_count=len(content))


def _make_state(classified: list) -> WorkflowState:
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "GB_TEST", "title": "t"},
        config={},
        rules_dir="/tmp",
        raw_chunks=[],
        classified_chunks=classified,
        final_chunks=[],
        errors=[],
    )


def test_transform_node_produces_final_chunks():
    """验证 transform_node 会调用 apply_strategy 并产生 chunk（通过 patch 避免真实 LLM 依赖）。"""
    classified = [
        ClassifiedChunk(
            raw_chunk=_raw("普通文本内容"),
            segments=[_seg("普通文本内容", "plain_text")],
            has_unknown=False,
        )
    ]

    from app.core.parser_workflow.nodes import transform_node as tn

    called = {}

    def _fake_apply_strategy(segments, raw_chunk, doc_metadata, config):
        called["args"] = (segments, raw_chunk, doc_metadata, config)
        return [
            {
                "chunk_id": "dummy",
                "doc_metadata": doc_metadata,
                "section_path": raw_chunk["section_path"],
                "content_type": segments[0]["content_type"],
                "content": "dummy",
                "raw_content": raw_chunk["content"],
                "meta": {},
            }
        ]

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(tn, "apply_strategy", _fake_apply_strategy)

    try:
        result = transform_node(_make_state(classified))
    finally:
        monkeypatch.undo()

    assert len(result["final_chunks"]) == 1


def test_llm_transform_uses_helper_and_produces_chunk(monkeypatch):
    from app.core.parser_workflow.nodes import transform_node as tn

    seg = _seg("原始内容", "formula", "llm_transform")
    seg["transform_params"]["prompt_template"] = "PROMPT {content}"
    raw = _raw("原始内容")

    called = {}

    def _fake_llm(content, transform_params, config):
        called["args"] = (content, transform_params, config)
        return "转写结果"

    monkeypatch.setattr(tn, "_call_llm_transform", _fake_llm)
    chunks = apply_strategy(
        [seg],
        raw,
        {"standard_no": "GB_TEST", "title": "t"},
        {"transform_model": "gpt-mock"},
    )

    assert called
    assert len(chunks) == 1
    c = chunks[0]
    assert c["content"] == "转写结果"
    assert c["raw_content"] == "原始内容"
    assert c["meta"]["transform_strategy"] == "llm_transform"
    assert c["meta"]["segment_raw_content"] == "原始内容"

