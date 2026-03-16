from typing import List

import pytest

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.nodes.escalate_node import escalate_node
from .test_utils import ensure_llm_api_key, get_logger, get_rules_dir, load_sample_markdown

logger = get_logger("escalate_node_real_llm")


@pytest.fixture(autouse=True)
def _ensure_llm_key():
    ensure_llm_api_key()


def _build_state_with_unknown_segments() -> WorkflowState:
    md_content, _ = load_sample_markdown()
    rules_dir = get_rules_dir()

    # 取一小段真实内容作为 unknown 片段
    sample_text = md_content[:200]

    raw = RawChunk(content=sample_text, section_path=["TEST"], char_count=len(sample_text))

    segments: List[TypedSegment] = [
        TypedSegment(
            content=sample_text,
            content_type="unknown",
            transform_params={
                "strategy": "plain_embed",
                "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
            },
            confidence=0.3,
            escalated=False,
        )
    ]

    classified = ClassifiedChunk(
        raw_chunk=raw,
        segments=segments,
        has_unknown=True,
    )

    return WorkflowState(
        md_content=md_content,
        doc_metadata={
            "standard_no": "GB1886.47-2016",
        },
        config={},
        rules_dir=str(rules_dir),
        raw_chunks=[],
        classified_chunks=[classified],
        final_chunks=[],
        errors=[],
    )


def test_escalate_node_reclassifies_unknown_segments_with_real_llm_and_rules():
    """
    构造带有 unknown 段落的 ClassifiedChunk，验证 escalate_node 能使用真实规则 + LLM 进行升级：
    - 将 unknown 片段映射到已有或新建 content_type
    - 设置 escalated=True, confidence=1.0
    - 清除 has_unknown 标记
    """
    state = _build_state_with_unknown_segments()

    result = escalate_node(state)
    classified_chunks: List[ClassifiedChunk] = result["classified_chunks"]

    assert classified_chunks, "escalate_node 应该返回至少一个 ClassifiedChunk"

    cc = classified_chunks[0]
    logger.info("escalated ClassifiedChunk: %s", cc)

    assert cc["has_unknown"] is False, "escalate_node 之后 should 清除 has_unknown 标记"

    for idx, seg in enumerate(cc["segments"]):
        logger.info(
            "segment[%d]: type=%s, confidence=%s, escalated=%s, content_preview=%r",
            idx,
            seg.get("content_type"),
            seg.get("confidence"),
            seg.get("escalated"),
            (seg.get("content") or "")[:80],
        )
        assert seg.get("content_type") != "unknown", "升级后 segment 不应再是 unknown"
        assert seg.get("escalated") is True, "升级后的 segment 应标记 escalated=True"
        assert seg.get("confidence") == 1.0, "升级后的 segment 置信度设为 1.0"

