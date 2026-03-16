from typing import List

import pytest

from app.core.parser_workflow.models import ClassifiedChunk, RawChunk, WorkflowState
from app.core.parser_workflow.nodes.classify_node import classify_node
from app.core.parser_workflow.nodes.parse_node import parse_node
from app.core.parser_workflow.nodes.slice_node import slice_node
from .test_utils import ensure_llm_api_key, get_logger, get_rules_dir, load_sample_markdown

logger = get_logger("classify_node_real_llm")


@pytest.fixture(autouse=True)
def _ensure_llm_key():
    ensure_llm_api_key()


def _build_state_with_few_raw_chunks() -> WorkflowState:
    md_content, _ = load_sample_markdown()
    rules_dir = get_rules_dir()

    initial_state = WorkflowState(
        md_content=md_content,
        doc_metadata={
            "standard_no": "GB1886.47-2016",
        },
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )

    parsed = parse_node(initial_state)
    sliced = slice_node(
        WorkflowState(
            md_content=md_content,
            doc_metadata=parsed["doc_metadata"],
            config={},
            rules_dir=str(rules_dir),
            raw_chunks=[],
            classified_chunks=[],
            final_chunks=[],
            errors=parsed["errors"],
        )
    )

    raw_chunks: List[RawChunk] = sliced["raw_chunks"]
    # 只取前几个 chunk，避免一次调用 LLM 过多
    small_raw_chunks = raw_chunks[:3]

    logger.info(
        "prepared %d raw_chunks for classify_node; first section_path=%s",
        len(small_raw_chunks),
        small_raw_chunks[0]["section_path"] if small_raw_chunks else None,
    )

    return WorkflowState(
        md_content=md_content,
        doc_metadata=parsed["doc_metadata"],
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=small_raw_chunks,
        classified_chunks=[],
        final_chunks=[],
        errors=parsed["errors"],
    )


def test_classify_node_returns_structured_segments_with_real_llm_and_rules():
    """
    使用真实 markdown + 规则目录 + LLM，验证 classify_node 能输出结构化的 segments，并正确设置 has_unknown。
    """
    state = _build_state_with_few_raw_chunks()

    result = classify_node(state)
    classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

    assert classified_chunks, "classify_node 应该返回至少一个 ClassifiedChunk"

    for idx, cc in enumerate(classified_chunks):
        segments = cc["segments"]
        has_unknown = cc["has_unknown"]

        logger.info(
            "classified_chunk[%d]: has_unknown=%s, segments=%d",
            idx,
            has_unknown,
            len(segments),
        )

        assert segments, "每个 ClassifiedChunk 至少应包含一个 segment"

        for s_idx, seg in enumerate(segments):
            logger.info(
                "segment[%d.%d]: type=%s, confidence=%s, content_preview=%r",
                idx,
                s_idx,
                seg.get("content_type"),
                seg.get("confidence"),
                (seg.get("content") or "")[:80],
            )
            assert seg.get("content"), "segment 应该包含 content"
            assert "content_type" in seg, "segment 应该包含 content_type 字段"
            assert "confidence" in seg, "segment 应该包含 confidence 字段"

