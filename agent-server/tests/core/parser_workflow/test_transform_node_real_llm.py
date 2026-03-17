from typing import List

import pytest

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    DocumentChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.nodes.transform_node import transform_node
from app.core.parser_workflow.rules import RulesStore
from .test_utils import ensure_llm_api_key, get_logger, get_rules_dir, load_sample_markdown

logger = get_logger("transform_node_real_llm")


@pytest.fixture(autouse=True)
def _ensure_llm_key():
    ensure_llm_api_key()


def _build_state_for_transform() -> WorkflowState:
    md_content, _ = load_sample_markdown()
    rules_dir = get_rules_dir()
    store = RulesStore(str(rules_dir))

    # 取一段真实内容，并使用某个已存在的 content_type 的 transform_params
    sample_text = md_content[:200]
    content_type_rules = store.get_content_type_rules().get("content_types", [])
    assert content_type_rules, "规则中应至少定义一个 content_type"

    first_type = content_type_rules[0]
    ct_id = first_type["id"]
    transform_params = store.get_transform_params(ct_id)

    raw = RawChunk(content=sample_text, section_path=["TEST"], char_count=len(sample_text))
    segments: List[TypedSegment] = [
        TypedSegment(
            content=sample_text,
            content_type=ct_id,
            transform_params=transform_params,
            confidence=0.9,
            escalated=False,
        )
    ]

    classified = ClassifiedChunk(
        raw_chunk=raw,
        segments=segments,
        has_unknown=False,
    )

    return WorkflowState(
        md_content=md_content,
        doc_metadata={
            "standard_no": "GB1886.47-2016",
            "doc_type": "TEST",
        },
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[classified],
        final_chunks=[],
        errors=[],
    )


def test_transform_node_generates_document_chunks_with_real_llm_and_rules():
    """
    使用真实规则 + LLM，验证 transform_node 能将 TypedSegment 转写为 DocumentChunk：
    - 生成非空 final_chunks
    - 每个 chunk 字段齐全，meta 中包含 transform_strategy 和 segment_raw_content
    """
    state = _build_state_for_transform()
    

    result = transform_node(state)
    final_chunks: List[DocumentChunk] = result["final_chunks"]
    logger.info(f"final_chunks: {final_chunks}")

    assert final_chunks, "transform_node 应该生成至少一个 DocumentChunk"

    for idx, chunk in enumerate(final_chunks):
        logger.info(
            "chunk[%d]: type=%s, id=%s, content_preview=%r, meta=%s",
            idx,
            chunk["content_type"],
            chunk["chunk_id"],
            (chunk["content"] or "")[:80],
            chunk["meta"],
        )
        assert chunk["chunk_id"], "DocumentChunk 应该包含 chunk_id"
        assert chunk["content_type"], "DocumentChunk 应该包含 content_type"
        assert chunk["content"], "DocumentChunk 应该包含 content"
        assert chunk["raw_content"], "DocumentChunk 应该保留原始 raw_content"
        assert "transform_strategy" in chunk["meta"], "meta 中应包含 transform_strategy"
        assert "segment_raw_content" in chunk["meta"], "meta 中应包含 segment_raw_content"

