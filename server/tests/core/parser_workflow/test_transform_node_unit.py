import pytest
from unittest.mock import patch

from worflow_parser_kb.models import (
    ClassifiedChunk, RawChunk, TypedSegment, WorkflowState,
)
from worflow_parser_kb.nodes.output import TransformOutput
from worflow_parser_kb.nodes.transform_node import transform_node

# 长段文本（> 50 字符），确保触发 LLM 调用路径（apply_strategy 中 len(content) < 50 短路）
_SEG1_CONTENT = "称取 $4\\mathrm{g}$ 试样，精确至 0.0001 g，置于已恒重的蒸发皿中，加入适量蒸馏水使其完全溶解"
_SEG2_CONTENT = "于电炉上缓缓加热溶解，注意避免局部过热，沸腾后继续保持沸腾状态 5 分钟，随后取出冷却至室温后进行滴定操作"


def _make_state(structure_type: str, semantic_type: str) -> WorkflowState:
    seg = TypedSegment(
        content="称取试样",
        structure_type=structure_type,
        semantic_type=semantic_type,
        transform_params={"strategy": "plain_embed", "prompt_template": "请转化：\n"},
        confidence=0.9,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    raw_chunk = RawChunk(content="称取试样", section_path=["A.3"], char_count=5)
    classified = ClassifiedChunk(raw_chunk=raw_chunk, segments=[seg], has_unknown=False)
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "TEST001"},
        config={},
        rules_dir="",
        raw_chunks=[raw_chunk],
        classified_chunks=[classified],
        final_chunks=[],
        errors=[],
    )


@pytest.mark.asyncio
async def test_transform_node_output_chunk_has_dual_type_fields():
    """transform_node 产出的 DocumentChunk 应包含 structure_type + semantic_type"""
    with patch(
        "worflow_parser_kb.nodes.transform_node._call_llm_transform",
        return_value="规范化文本",
    ):
        result = await transform_node(_make_state("list", "procedure"))

    chunks = result["final_chunks"]
    assert chunks
    chunk = chunks[0]
    assert chunk["structure_type"] == "list"
    assert chunk["semantic_type"] == "procedure"
    assert "content_type" not in chunk


def _make_state_for_transform(latex_text: str, section_path: list, standard_no: str) -> WorkflowState:
    """构建含多 segment 的 state，用于 raw_content 对比测试。"""
    raw_chunk = RawChunk(
        content=latex_text,
        section_path=section_path,
        char_count=len(latex_text),
    )
    seg1 = TypedSegment(
        content=_SEG1_CONTENT,
        structure_type="list",
        semantic_type="procedure",
        transform_params={"strategy": "plain_embed", "prompt_template": "请转化：\n"},
        confidence=0.9,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    seg2 = TypedSegment(
        content=_SEG2_CONTENT,
        structure_type="paragraph",
        semantic_type="procedure",
        transform_params={"strategy": "plain_embed", "prompt_template": "请转化：\n"},
        confidence=0.9,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )
    classified = ClassifiedChunk(raw_chunk=raw_chunk, segments=[seg1, seg2], has_unknown=False)
    return WorkflowState(
        md_content="",
        doc_metadata={"standard_no": standard_no},
        config={},
        rules_dir="",
        raw_chunks=[raw_chunk],
        classified_chunks=[classified],
        final_chunks=[],
        errors=[],
    )


@pytest.mark.asyncio
async def test_transform_node_raw_content_is_raw_chunk_content():
    """transform_node 的 raw_content 应为 raw_chunk["content"]（整节原文），而非 seg["content"]。
    同一 raw_chunk 的多个 segment 产出的 chunks 共享同一 raw_content，
    以便 merge_node 能正确识别同源 chunk 并合并。"""
    latex_text = "称取 $4\\mathrm{g}$ 试样于烧杯中"
    captured_args = []

    def capture_transform(content, transform_params, ref_context=""):
        captured_args.append({"content": content, "transform_params": transform_params})
        return content

    with patch("worflow_parser_kb.nodes.transform_node._call_llm_transform", side_effect=capture_transform):
        state = _make_state_for_transform(latex_text, ["5.1"], "GB 5009.3")
        result = await transform_node(state)

    assert len(captured_args) == 2
    assert captured_args[0]["content"] == _SEG1_CONTENT
    assert captured_args[1]["content"] == _SEG2_CONTENT

    chunks = result["final_chunks"]
    assert len(chunks) == 2
    # raw_content = raw_chunk["content"]，两个 chunk 共享同一个值
    assert chunks[0]["raw_content"] == latex_text
    assert chunks[1]["raw_content"] == latex_text
    # segment 各自的原始文本存放在 meta.segment_raw_content
    assert chunks[0]["meta"]["segment_raw_content"] == _SEG1_CONTENT
    assert chunks[1]["meta"]["segment_raw_content"] == _SEG2_CONTENT


@pytest.mark.asyncio
async def test_transform_node_concurrent_execution_with_exceptions():
    """transform_node 并发执行时，return_exceptions=True 保证部分失败不影响整体"""
    from worflow_parser_kb.nodes.transform_node import transform_node
    from kb.models import DocumentChunk
    from worflow_parser_kb.models import WorkflowState, ClassifiedChunk, RawChunk, TypedSegment

    # 3 个 classified chunks：2 个成功，1 个超时
    classified_chunks = [
        ClassifiedChunk(
            raw_chunk=RawChunk(content="c0", section_path=["A.1"], char_count=3),
            segments=[
                TypedSegment(
                    content="x",
                    structure_type="paragraph",
                    semantic_type="scope",
                    transform_params={"strategy": "plain_embed", "prompt_template": ""},
                    confidence=0.9,
                    escalated=False,
                    cross_refs=[],
                    ref_context="",
                    failed_table_refs=[],
                )
            ],
            has_unknown=False,
        ),
        ClassifiedChunk(
            raw_chunk=RawChunk(content="c1", section_path=["A.2"], char_count=3),
            segments=[
                TypedSegment(
                    content="y",
                    structure_type="paragraph",
                    semantic_type="scope",
                    transform_params={"strategy": "plain_embed", "prompt_template": ""},
                    confidence=0.9,
                    escalated=False,
                    cross_refs=[],
                    ref_context="",
                    failed_table_refs=[],
                )
            ],
            has_unknown=False,
        ),
        ClassifiedChunk(
            raw_chunk=RawChunk(content="c2", section_path=["A.3"], char_count=3),
            segments=[
                TypedSegment(
                    content="z",
                    structure_type="paragraph",
                    semantic_type="scope",
                    transform_params={"strategy": "plain_embed", "prompt_template": ""},
                    confidence=0.9,
                    escalated=False,
                    cross_refs=[],
                    ref_context="",
                    failed_table_refs=[],
                )
            ],
            has_unknown=False,
        ),
    ]

    state = WorkflowState(
        md_content="",
        doc_metadata={"standard_no": "TEST001"},
        config={},
        rules_dir="",
        raw_chunks=[],
        classified_chunks=classified_chunks,
        final_chunks=[],
        errors=[],
    )

    mock_chunk: DocumentChunk = {
        "chunk_id": "abc",
        "content": "normalized",
        "raw_content": "raw",
        "structure_type": "paragraph",
        "semantic_type": "scope",
        "section_path": ["A.1"],
        "doc_metadata": {"standard_no": "TEST001"},
        "meta": {},
    }

    async def mock_to_thread(func, *args, **kwargs):
        mock_to_thread.call_count += 1
        idx = mock_to_thread.call_count - 1
        if idx == 1:
            raise Exception("timeout")
        return [mock_chunk]

    mock_to_thread.call_count = 0

    with patch("worflow_parser_kb.nodes.transform_node.asyncio.to_thread", side_effect=mock_to_thread):
        result = await transform_node(state)

    assert len(result["final_chunks"]) == 2  # 2 个成功
    assert len(result["errors"]) == 1
    assert "timeout" in result["errors"][0]
    assert "transform_node[1]:" in result["errors"][0]
